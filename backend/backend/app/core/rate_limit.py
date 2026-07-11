"""
Simple in-memory rate limiter per IP address.

Limits:
  - /upload:   5 per day per IP
  - /analysis: 3 per day per IP  (expensive — multiple Gemini calls)
  - /chat:     20 per day per IP (one Gemini call each)

Resets daily. In-memory — resets on container restart, which is fine
for a portfolio project.
"""

import time
import logging
from collections import defaultdict
from functools import wraps

from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# { ip: { endpoint: [(timestamp, ...)] } }
_requests: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

LIMITS = {
    "upload":   5,
    "analysis": 3,
    "chat":     20,
}

WINDOW_SECONDS = 86400  # 24 hours


def _clean_old(entries: list[float], window: int) -> list[float]:
    """Remove entries older than the window."""
    cutoff = time.time() - window
    return [t for t in entries if t > cutoff]


def check_rate_limit(request: Request, endpoint: str) -> None:
    """
    Check if the request is within rate limits.
    Raises HTTPException 429 if exceeded.
    """
    ip = request.client.host if request.client else "unknown"
    limit = LIMITS.get(endpoint, 10)

    # Clean old entries
    _requests[ip][endpoint] = _clean_old(_requests[ip][endpoint], WINDOW_SECONDS)

    if len(_requests[ip][endpoint]) >= limit:
        remaining_seconds = int(WINDOW_SECONDS - (time.time() - _requests[ip][endpoint][0]))
        hours = remaining_seconds // 3600
        logger.warning(f"Rate limit hit: {ip} on /{endpoint} ({limit}/day)")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded — maximum {limit} requests per day for this endpoint. Resets in ~{hours}h.",
        )

    # Record this request
    _requests[ip][endpoint].append(time.time())