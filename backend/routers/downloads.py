"""Download endpoints for fingerprint tools."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(prefix="/downloads", tags=["Downloads"])


def _resolve_bundle_path() -> Path:
    env_path = os.getenv("ZIONSCAN_BUNDLE_PATH")
    if env_path:
        return Path(env_path)
    root = Path(__file__).resolve().parents[2]
    return root / "app" / "downloads" / "ZionScanBundle.zip"


@router.get("/zionscan")
def download_zionscan():
    bundle_url = os.getenv("ZIONSCAN_BUNDLE_URL")
    if bundle_url:
        return RedirectResponse(bundle_url)

    path = _resolve_bundle_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Bundle not found")

    return FileResponse(
        path=path,
        filename="ZionScanBundle.zip",
        media_type="application/zip",
    )
