from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass
class RequestContext:
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None


_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context", default=None
)


def set_request_context(context: RequestContext):
    return _request_context.set(context)


def reset_request_context(token) -> None:
    _request_context.reset(token)


def get_request_context() -> Optional[RequestContext]:
    return _request_context.get()
