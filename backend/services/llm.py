"""LLM helper for parsing invoice text via OpenAI-compatible API."""

from __future__ import annotations

import base64
import json
import logging
import os
from io import BytesIO
from typing import Any, Dict, Optional

from openai import OpenAI
try:
    from openai import DefaultHttpxClient
except Exception:  # noqa: BLE001
    DefaultHttpxClient = None
from pdf2image import convert_from_bytes
from PIL import Image

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4.1"
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL") or OPENAI_MODEL
OPENAI_PROXY_URL = os.getenv("OPENAI_PROXY_URL")


def _get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    http_client = None
    if OPENAI_PROXY_URL and DefaultHttpxClient is not None:
        try:
            http_client = DefaultHttpxClient(proxy=OPENAI_PROXY_URL)
        except TypeError:
            http_client = DefaultHttpxClient(proxies=OPENAI_PROXY_URL)
    elif OPENAI_PROXY_URL:
        logger.warning("OPENAI_PROXY_URL is set but DefaultHttpxClient is unavailable")
    if http_client is not None:
        return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None, http_client=http_client)
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)


def _encode_image(content: bytes, filename: Optional[str]) -> tuple[str, bytes]:
    """Return (mime, image_bytes) for vision input. PDF -> first page jpeg."""
    mime = "image/png"
    data = content
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            pages = convert_from_bytes(content, first_page=1, last_page=1)
            buf = BytesIO()
            pages[0].save(buf, format="JPEG")
            data = buf.getvalue()
            mime = "image/jpeg"
        elif name.endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        elif name.endswith(".png"):
            mime = "image/png"
        else:
            img = Image.open(BytesIO(content))
            buf = BytesIO()
            img.save(buf, format="JPEG")
            data = buf.getvalue()
            mime = "image/jpeg"
    except Exception:
        data = content
    return mime, data


def _parse_llm_json(content: str) -> Dict[str, Any]:
    if not content:
        raise RuntimeError("Empty LLM response")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise


def analyze_invoice_text_llm(text: str) -> Dict[str, Any]:
    """Send OCR text to LLM and extract fields."""
    client = _get_client()
    system_prompt = (
        "Ты парсишь текст счета. Верни строго JSON с полями:\n"
        "- amount: итоговая сумма к оплате (число, без валюты, два знака через точку).\n"
        "- payee: кто выставил счет (продавец/поставщик).\n"
        "- inn: ИНН продавца, если найден.\n"
        "- purpose: краткое назначение платежа (2-12 слов, сжать перечень товаров/услуг).\n"
        "- invoice_date: дата счета YYYY-MM-DD, если есть в документе.\n"
        "- sent_at: дата заявки/отправки, если явно указана (YYYY-MM-DD), иначе null.\n"
        "- comment: опциональный комментарий, иначе null.\n"
        "Если нет данных по полю — верни null."
    )
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:8000]},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("OpenAI request failed")
        raise RuntimeError("LLM request failed") from exc

    content = resp.choices[0].message.content if resp.choices else ""
    return _parse_llm_json(content)


def analyze_invoice_image_llm(content: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
    """Send image/PDF to vision model and extract fields."""
    client = _get_client()
    mime, data = _encode_image(content, filename)
    b64 = base64.b64encode(data).decode("utf-8")
    system_prompt = (
        "Ты парсишь изображение/скан счета. Верни строго JSON с полями:\n"
        "- amount: итоговая сумма к оплате (число, без валюты, два знака через точку).\n"
        "- payee: кто выставил счет (продавец/поставщик).\n"
        "- inn: ИНН продавца, если найден.\n"
        "- purpose: краткое назначение платежа (2-12 слов, сжать перечень товаров/услуг).\n"
        "- invoice_date: дата счета YYYY-MM-DD.\n"
        "- sent_at: дата заявки/отправки, если явно указана (YYYY-MM-DD), иначе null.\n"
        "- comment: опциональный комментарий, иначе null.\n"
        "Если нет данных по полю — верни null."
    )
    user_content = [
        {"type": "text", "text": "Извлеки поля и верни JSON."},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "auto"}},
    ]
    try:
        resp = client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("OpenAI vision request failed")
        raise RuntimeError("LLM vision request failed") from exc

    content_resp = resp.choices[0].message.content if resp.choices else ""
    return _parse_llm_json(content_resp)
