from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

import urllib3

logger = logging.getLogger(__name__)

_FALSE_VALUES = {"0", "false", "no", "off"}


def _tls_verify_flag_enabled() -> bool:
    raw = (os.getenv("IIKO_VERIFY_TLS") or "").strip().lower()
    if not raw:
        return True
    return raw not in _FALSE_VALUES


@lru_cache(maxsize=1)
def get_iiko_tls_verify() -> bool | str:
    ca_bundle = (os.getenv("IIKO_CA_BUNDLE") or "").strip()
    if ca_bundle:
        bundle_path = Path(ca_bundle).expanduser()
        if not bundle_path.is_file():
            raise RuntimeError(f"IIKO_CA_BUNDLE does not exist: {bundle_path}")
        return str(bundle_path)

    if _tls_verify_flag_enabled():
        return True

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.warning("IIKO TLS verification disabled via IIKO_VERIFY_TLS=false")
    return False
