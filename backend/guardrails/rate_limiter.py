"""
Guardrail 2 — Rate Limiter
In-memory sliding window rate limiter per user/IP.
Prevents brute force login, API abuse, and runaway AI pipeline calls.

Limits enforced:
- Login attempts:   5 per minute per IP
- PDF uploads:      10 per hour per user
- AI analysis runs: 5 per hour per user
- NL queries:       20 per hour per user
"""

import time
import logging
from collections import defaultdict, deque
from threading import Lock
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int
    retry_after_seconds: Optional[int] = None


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self):
        self._windows: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        """
        Check if the given key is within its rate limit.
        key: unique identifier (e.g. "login:192.168.1.1" or "upload:user:42")
        """
        now = time.monotonic()
        window_start = now - window_seconds

        with self._lock:
            window = self._windows[key]

            # Evict timestamps outside the window
            while window and window[0] < window_start:
                window.popleft()

            current_count = len(window)
            remaining = max(0, limit - current_count - 1)

            if current_count >= limit:
                # Time until the oldest request leaves the window
                retry_after = max(1, int(window[0] - window_start) + 1) if window else 1
                logger.warning(
                    f"[GUARDRAIL:rate_limit] BLOCKED — key='{key}' "
                    f"count={current_count}/{limit} retry_after={retry_after}s"
                )
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_after_seconds=int(window_start + window_seconds - now) + 1,
                    retry_after_seconds=retry_after,
                )

            # Allow and record this request
            window.append(now)

        logger.debug(f"[GUARDRAIL:rate_limit] ALLOWED — key='{key}' count={current_count+1}/{limit}")
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining,
            reset_after_seconds=window_seconds,
        )

    def reset(self, key: str):
        """Reset the rate limit counter for a key (e.g. after successful login)."""
        with self._lock:
            if key in self._windows:
                del self._windows[key]


# ── Singleton limiter instance ────────────────────────────────────────────────
_limiter = SlidingWindowRateLimiter()


# ── Named limits ──────────────────────────────────────────────────────────────

def check_login_rate(ip: str) -> RateLimitResult:
    """5 login attempts per minute per IP address."""
    return _limiter.check(f"login:{ip}", limit=5, window_seconds=60)


def check_upload_rate(user_id: int) -> RateLimitResult:
    """10 PDF uploads per hour per user."""
    return _limiter.check(f"upload:user:{user_id}", limit=10, window_seconds=3600)


def check_analysis_rate(user_id: int) -> RateLimitResult:
    """5 AI analysis runs per hour per user (expensive pipeline)."""
    return _limiter.check(f"analyze:user:{user_id}", limit=5, window_seconds=3600)


def check_query_rate(user_id: int) -> RateLimitResult:
    """20 natural language queries per hour per user."""
    return _limiter.check(f"query:user:{user_id}", limit=20, window_seconds=3600)


def reset_login_rate(ip: str):
    """Reset login counter after successful login (good UX)."""
    _limiter.reset(f"login:{ip}")
