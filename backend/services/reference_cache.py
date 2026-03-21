from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable, Hashable, TypeVar, Any

T = TypeVar("T")


@dataclass
class _CacheEntry:
    expires_at: float
    value: Any


_CACHE_LOCK = RLock()
_CACHE_STORE: dict[tuple[str, Hashable], _CacheEntry] = {}


def cached_reference_data(
    scope: str,
    key: Hashable,
    loader: Callable[[], T],
    *,
    ttl_seconds: int = 60,
) -> T:
    cache_key = (str(scope), key)
    now = monotonic()

    with _CACHE_LOCK:
        entry = _CACHE_STORE.get(cache_key)
        if entry and entry.expires_at > now:
            return deepcopy(entry.value)
        if entry:
            _CACHE_STORE.pop(cache_key, None)

    value = loader()
    ttl = max(int(ttl_seconds), 0)
    if ttl <= 0:
        return value

    with _CACHE_LOCK:
        _CACHE_STORE[cache_key] = _CacheEntry(
            expires_at=now + ttl,
            value=deepcopy(value),
        )
    return deepcopy(value)


def invalidate_reference_scope(scope: str) -> None:
    normalized = str(scope)
    with _CACHE_LOCK:
        keys_to_drop = [key for key in _CACHE_STORE.keys() if key[0] == normalized]
        for key in keys_to_drop:
            _CACHE_STORE.pop(key, None)

