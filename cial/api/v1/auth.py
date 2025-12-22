"""
CIAL Authentication & Security API
Session 20: JWT authentication and API key management

Endpoints for token generation, API key creation, and security management.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from api.models.responses import VersionedResponse, error_response, success_response
from infrastructure.logging_config import logger
from infrastructure.observability import trace_operation
from infrastructure.rate_limiter import RateLimits, limiter
from infrastructure.security import (
    APIKey,
    APIKeyType,
    TokenData,
    get_current_user,
    get_security_manager,
    verify_api_key,
)

router = APIRouter()


# Request/Response models
class TokenRequest(BaseModel):
    """Request model for token creation."""

    username: str
    password: str | None = None  # For demo purposes
    scopes: list[str] = []


class APIKeyRequest(BaseModel):
    """Request model for API key creation."""

    name: str
    type: APIKeyType = APIKeyType.READ_ONLY
    rate_limit: int = 100
    metadata: dict[str, Any] | None = None


@router.post("/token")
@limiter.limit(RateLimits.STRICT)
@trace_operation("auth_create_token")
async def create_token(
    request: Request, token_request: TokenRequest
) -> VersionedResponse[dict[str, str]]:
    """
    Create JWT access token.

    **Note:** This is a simplified implementation for demonstration.
    In production, verify credentials against a user database.

    Args:
        request: FastAPI request object (required for rate limiting)
        token_request: Token request with username and optional password

    Returns:
        JWT access token with expiration time

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/auth/token" \
          -H "Content-Type: application/json" \
          -d '{
            "username": "demo_user",
            "scopes": ["read", "write"]
          }'
        ```
    """
    try:
        security_manager = get_security_manager()

        # Create token
        token = security_manager.create_access_token(
            data={"sub": token_request.username, "scopes": token_request.scopes}
        )

        return success_response(
            data={
                "access_token": token,
                "token_type": "bearer",
                "expires_in_minutes": 1440,  # 24 hours
            },
            message="Token created successfully",
        )

    except Exception as e:
        logger.error(f"Token creation failed: {e}", exc_info=True)
        return error_response(
            message="Failed to create token",
            error_code="TOKEN_CREATION_ERROR",
            details={"error": str(e)},
        )


@router.get("/verify")
@trace_operation("auth_verify_token")
async def verify_token(
    user: TokenData = Depends(get_current_user),  # noqa: B008
) -> VersionedResponse[dict[str, Any]]:
    """
    Verify JWT token and return decoded data.

    Requires valid JWT token in Authorization header.

    Returns:
        Decoded token data including username and scopes

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/auth/verify" \
          -H "Authorization: Bearer <your_token>"
        ```
    """
    return success_response(
        data={
            "username": user.username,
            "api_key": user.api_key[:20] + "..." if user.api_key else None,
            "scopes": user.scopes,
            "valid": True,
        },
        message="Token is valid",
    )


@router.post("/api-key")
@limiter.limit(RateLimits.ADMIN)
@trace_operation("auth_create_api_key")
async def create_api_key(
    request: Request, api_key_request: APIKeyRequest
) -> VersionedResponse[dict[str, Any]]:
    """
    Create a new API key.

    **Important:** The API key is returned only once and cannot be retrieved again.
    Store it securely!

    Args:
        request: FastAPI request object (required for rate limiting)
        api_key_request: API key configuration

    Returns:
        API key details including the key itself (only shown once)

    Security Levels:
    - `read_only`: Can only read data (GET requests)
    - `read_write`: Can read and write data (GET, POST, PUT)
    - `admin`: Full access including deletions and admin operations

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/auth/api-key" \
          -H "Content-Type: application/json" \
          -d '{
            "name": "My Trading Bot",
            "type": "read_write",
            "rate_limit": 200,
            "metadata": {"bot_version": "1.0"}
          }'
        ```
    """
    try:
        security_manager = get_security_manager()

        api_key_obj = security_manager.create_api_key(
            name=api_key_request.name,
            key_type=api_key_request.type,
            rate_limit=api_key_request.rate_limit,
            metadata=api_key_request.metadata,
        )

        return success_response(
            data={
                "api_key": api_key_obj.key,  # ⚠️ Only returned once!
                "name": api_key_obj.name,
                "type": api_key_obj.type.value,
                "rate_limit": api_key_obj.rate_limit,
                "created_at": api_key_obj.created_at.isoformat(),
                "warning": "⚠️ Store this API key securely. It cannot be retrieved again!",
            },
            message="API key created successfully",
        )

    except Exception as e:
        logger.error(f"API key creation failed: {e}", exc_info=True)
        return error_response(
            message="Failed to create API key",
            error_code="API_KEY_CREATION_ERROR",
            details={"error": str(e)},
        )


@router.get("/api-keys")
@limiter.limit(RateLimits.ADMIN)
@trace_operation("auth_list_api_keys")
async def list_api_keys(
    request: Request,
    include_inactive: bool = Query(False, description="Include revoked keys"),  # noqa: B008
) -> VersionedResponse[dict[str, Any]]:
    """
    List all API keys (without the actual key values).

    Returns API key metadata but NOT the actual keys (those are shown only once
    upon creation).

    Args:
        request: FastAPI request object (required for rate limiting)
        include_inactive: Whether to include revoked/inactive keys

    Returns:
        List of API keys with metadata
    """
    try:
        security_manager = get_security_manager()
        keys = security_manager.list_api_keys(include_inactive=include_inactive)

        return success_response(
            data={"api_keys": keys, "total": len(keys)}, message="API keys retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Failed to list API keys: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve API keys",
            error_code="API_KEY_LIST_ERROR",
            details={"error": str(e)},
        )


@router.delete("/api-key/revoke")
@limiter.limit(RateLimits.ADMIN)
@trace_operation("auth_revoke_api_key")
async def revoke_api_key(
    request: Request, api_key: str = Query(..., description="API key to revoke")  # noqa: B008
) -> VersionedResponse[dict[str, Any]]:
    """
    Revoke an API key.

    Revoked keys can no longer be used for authentication.

    Args:
        request: FastAPI request object (required for rate limiting)
        api_key: The API key to revoke

    Returns:
        Revocation status

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/v1/auth/api-key/revoke?api_key=cial_xxx"
        ```
    """
    try:
        security_manager = get_security_manager()
        success = security_manager.revoke_api_key(api_key)

        if success:
            return success_response(data={"revoked": True}, message="API key revoked successfully")
        else:
            return error_response(message="API key not found", error_code="API_KEY_NOT_FOUND")

    except Exception as e:
        logger.error(f"API key revocation failed: {e}", exc_info=True)
        return error_response(
            message="Failed to revoke API key",
            error_code="API_KEY_REVOKE_ERROR",
            details={"error": str(e)},
        )


@router.get("/api-key/validate")
@trace_operation("auth_validate_api_key")
async def validate_api_key_endpoint(
    api_key_obj: APIKey = Depends(verify_api_key),  # noqa: B008
) -> VersionedResponse[dict[str, Any]]:
    """
    Validate an API key and return its details.

    Requires valid API key in Authorization header or query parameter.

    Returns:
        API key details and validation status

    Example:
        ```bash
        # Header authentication
        curl "http://localhost:8000/api/v1/auth/api-key/validate" \
          -H "Authorization: Bearer cial_xxx"

        # Query parameter
        curl "http://localhost:8000/api/v1/auth/api-key/validate?api_key=cial_xxx"
        ```
    """
    return success_response(
        data={
            "valid": True,
            "name": api_key_obj.name,
            "type": api_key_obj.type.value,
            "rate_limit": api_key_obj.rate_limit,
            "last_used": api_key_obj.last_used.isoformat() if api_key_obj.last_used else None,
            "created_at": api_key_obj.created_at.isoformat(),
        },
        message="API key is valid",
    )


@router.get("/stats")
@limiter.limit(RateLimits.ADMIN)
@trace_operation("auth_stats")
async def get_security_stats(request: Request) -> VersionedResponse[dict[str, Any]]:
    """
    Get security and authentication statistics.

    Args:
        request: FastAPI request object (required for rate limiting)

    Returns:
        Security metrics including auth attempts, API key counts, etc.
    """
    try:
        security_manager = get_security_manager()
        stats = security_manager.get_stats()

        return success_response(data=stats, message="Security statistics retrieved")

    except Exception as e:
        logger.error(f"Failed to get security stats: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve security statistics",
            error_code="SECURITY_STATS_ERROR",
            details={"error": str(e)},
        )


@router.get("/health")
async def security_health() -> VersionedResponse[dict[str, str]]:
    """
    Check security system health.

    Returns:
        Security health status
    """
    try:
        security_manager = get_security_manager()
        stats = security_manager.get_stats()

        return success_response(
            data={
                "status": "healthy",
                "active_api_keys": stats.get("active_api_keys", 0),
                "auth_success_rate": f"{(stats['auth_successes'] / max(stats['auth_attempts'], 1)) * 100:.1f}%",
            },
            message="Security system is healthy",
        )

    except Exception as e:
        logger.error(f"Security health check failed: {e}", exc_info=True)
        return error_response(
            message="Security health check failed",
            error_code="SECURITY_HEALTH_ERROR",
            details={"error": str(e)},
        )
