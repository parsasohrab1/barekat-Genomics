"""Request rate limiting for the partner API (in-memory)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit_per_minute: int) -> bool:
        now = time.time()
        window = 60.0
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit_per_minute:
                return False
            q.append(now)
            return True


_limiter = InMemoryRateLimiter()


class PartnerRateLimitMiddleware(BaseHTTPMiddleware):
    """Limits only /api/v1/partner/* paths."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if "/partner/" in path:
            api_key = request.headers.get("X-API-Key") or ""
            limit = int(request.headers.get("X-RateLimit-Override", "60") or 60)
            bucket = api_key[:24] or (request.client.host if request.client else "anon")
            # the actual limit is set from the partner route state; default 60
            limit = getattr(request.state, "partner_rate_limit", limit)
            if not _limiter.allow(f"partner:{bucket}", limit):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Partner API request rate limit exceeded",
                )
        return await call_next(request)


def check_partner_rate(key_id: str, limit_per_minute: int) -> None:
    if not _limiter.allow(f"partner:{key_id}", limit_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Partner API request rate limit exceeded",
        )
