from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_ROOT = PROJECT_ROOT / "media"

INVALID_FILENAME_CHARS = "<>:/\|?*"
INVALID_PATTERN = re.compile(f"[{re.escape(INVALID_FILENAME_CHARS)}]")


def ensure_media_dir() -> Path:
    """Ensure that the media directory exists and return its path."""
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return MEDIA_ROOT


def sanitize_filename(name: str) -> str:
    """Make sure filename does not contain forbidden characters."""
    cleaned = INVALID_PATTERN.sub("_", name.strip())
    cleaned = cleaned.replace("\0", "")
    cleaned = cleaned.strip()
    return cleaned or "item"


def build_media_path(name: str, extension: str) -> Path:
    """Return a unique media path for a given name and extension."""
    ensure_media_dir()
    stem = sanitize_filename(name)
    ext = f".{extension.lstrip('.')}" if extension else ""
    candidate = MEDIA_ROOT / f"{stem}{ext}"
    suffix = 1
    while candidate.exists():
        candidate = MEDIA_ROOT / f"{stem}_{suffix}{ext}"
        suffix += 1
    return candidate


def media_relative_path(path: Path) -> str:
    """Return project-relative path for storage in DB."""
    return str(path.relative_to(PROJECT_ROOT))


def resolve_media_path(relative: str) -> Path:
    """Convert stored project-relative path into an absolute Path inside media directory."""
    if not relative:
        raise ValueError("relative path must be provided")
    ensure_media_dir()
    abs_path = (PROJECT_ROOT / relative).resolve()
    media_root = MEDIA_ROOT.resolve()
    if media_root not in abs_path.parents and abs_path != media_root:
        raise ValueError("path escapes media directory")
    return abs_path
