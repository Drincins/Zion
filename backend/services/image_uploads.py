from __future__ import annotations

import os
from io import BytesIO

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError


def normalize_uploaded_image(
    *,
    filename: str | None,
    content: bytes,
    content_type: str | None,
) -> tuple[str, bytes, str]:
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    upload_filename = filename or "photo.jpg"
    upload_content = content
    upload_content_type = content_type or "application/octet-stream"

    try:
        img = Image.open(BytesIO(content))
        img_format = (img.format or "").upper()
        if img_format != "JPEG" or upload_content_type not in {"image/jpeg", "image/jpg"}:
            if img.mode in {"RGBA", "LA"} or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[-1])
                img = background
            else:
                img = img.convert("RGB")
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=90)
            upload_content = buf.getvalue()
            upload_content_type = "image/jpeg"
            base = os.path.splitext(upload_filename)[0] or "photo"
            upload_filename = f"{base}.jpg"
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image format") from exc

    return upload_filename, upload_content, upload_content_type
