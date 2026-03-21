"""Local OCR helpers using Tesseract (rus+eng)."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, List, Optional

import pdf2image
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def _load_images(content: bytes, filename: str | None = None) -> List[Image.Image]:
    if filename and filename.lower().endswith(".pdf"):
        # convert PDF pages to images
        return pdf2image.convert_from_bytes(content)
    # assume image
    return [Image.open(BytesIO(content))]


def detect_lines(content: bytes, filename: str | None = None) -> List[str]:
    """Run Tesseract and return detected lines of text."""
    try:
        images = _load_images(content, filename)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load file for OCR")
        raise RuntimeError("Failed to read file for OCR") from exc

    lines: List[str] = []
    for img in images:
        text = pytesseract.image_to_string(img, lang="rus+eng")
        lines.extend([line for line in text.splitlines() if line.strip()])
    return lines


def _try_parse_amount(lines: List[str]) -> Optional[str]:
    amount_regex = re.compile(r"(?<!\d)(\d{1,3}(?:[ \u00A0]?\d{3})*(?:[.,]\d{2})?)")
    candidates: List[Decimal] = []
    for line in lines:
        for match in amount_regex.findall(line):
            normalized = match.replace("\u00A0", " ").replace(" ", "").replace(",", ".")
            try:
                candidates.append(Decimal(normalized))
            except Exception:  # noqa: BLE001
                continue
    if not candidates:
        return None
    best = max(candidates)
    return f"{best:.2f}"


def _try_parse_date(lines: List[str]) -> Optional[str]:
    date_regex = re.compile(r"\b(\d{2}[./-]\d{2}[./-]\d{2,4})\b")
    for line in lines:
        m = date_regex.search(line)
        if m:
            return m.group(1).replace("/", "-")
    return None


def _try_parse_payee(lines: List[str]) -> Optional[str]:
    for line in lines:
        lower = line.lower()
        if "ооо" in lower or "ип " in lower or "ao" in lower or "зао" in lower:
            return line.strip()
    for line in lines:
        if line and len(line.strip()) > 3:
            return line.strip()
    return None


def _try_parse_purpose(lines: List[str]) -> Optional[str]:
    for line in lines:
        lower = line.lower()
        if "назнач" in lower or "оплат" in lower or "за " in lower:
            return line.strip()
    return None


def analyze_invoice_content(content: bytes, filename: str | None = None) -> Dict[str, Any]:
    lines = detect_lines(content, filename)
    text = "\n".join(lines)
    result: Dict[str, Any] = {
        "lines": lines,
        "text": text,
        "amount": _try_parse_amount(lines),
        "payee": _try_parse_payee(lines),
        "purpose": _try_parse_purpose(lines),
        "sent_at": _try_parse_date(lines),
    }
    return result
