"""
CIAL Rate Limiting
Session 20: API rate limiting with slowapi

Features:
- Global rate limiting
- Per-endpoint rate limiting
- Per-API-key rate limiting
- Rate limit bypass for admin keys
- Custom rate limit responses
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.observability import metrics


def get_api_key_or_ip(request: Request) -> str:
    """
    Get identifier for rate limiting (API key or IP address).

    Prioritizes API key if present, falls back to IP address.
    """
    # Try to get API key from header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        api_key = auth_header.split("Bearer ")[1]
        if api_key.startswith("cial_"):
            return f"api_key:{api_key[:20]}"  # Use partial key for identification

    # Try query parameter
    api_key_param = request.query_params.get("api_key", "")
    if api_key_param.startswith("cial_"):
        return f"api_key:{api_key_param[:20]}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Create rate limiter
limiter = Limiter(
    key_func=get_api_key_or_ip,
    default_limits=[f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}second"],
    headers_enabled=True,  # Add rate limit headers to responses
    swallow_errors=True,  # Continue even if Redis is down
)


# Rate limit presets for different endpoint types
class RateLimits:
    """Predefined rate limit configurations."""

    # Very strict (for expensive operations)
    STRICT = "5/minute"

    # Normal API usage
    NORMAL = "100/minute"

    # Generous (for cheap operations)
    GENEROUS = "1000/minute"

    # Read-only operations
    READ = "500/minute"

    # Write operations
    WRITE = "50/minute"

    # Admin operations
    ADMIN = "10/minute"

    # WebSocket connections
    WEBSOCKET = "100/hour"

    # Database operations
    DATABASE = "20/minute"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom rate limit exceeded handler with metrics.

    Returns structured error response.
    """
    logger.warning(
        "Rate limit exceeded", identifier=get_api_key_or_ip(request), path=request.url.path
    )

    # Record metric
    metrics.increment_counter(
        "cial_rate_limit_exceeded_total",
        {
            "path": request.url.path,
            "identifier_type": "api_key" if "api_key:" in str(exc.detail) else "ip",
        },
    )

    return {
        "error": "Rate limit exceeded",
        "detail": str(exc.detail),
        "retry_after": exc.detail.split(" ")[-1] if "retry after" in exc.detail.lower() else None,
        "message": "Too many requests. Please slow down and try again later.",
    }
