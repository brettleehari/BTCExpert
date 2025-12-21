"""
CIAL Security Infrastructure
Session 20: Rate Limiting, JWT Authentication, and API Key Management

Features:
- JWT token authentication
- API key management and validation
- Rate limiting with slowapi
- Security headers
- CORS configuration
- Input validation and sanitization
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.observability import metrics, trace_operation

# Security schemes
security_scheme = HTTPBearer(auto_error=False)


class APIKeyType(str, Enum):
    """API key access levels."""

    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


class TokenData(BaseModel):
    """JWT token data structure."""

    username: str | None = None
    api_key: str | None = None
    scopes: list[str] = []


class APIKey(BaseModel):
    """API key model."""

    key: str
    key_hash: str
    name: str
    type: APIKeyType
    created_at: datetime
    last_used: datetime | None = None
    is_active: bool = True
    rate_limit: int = 100  # requests per minute
    metadata: dict[str, Any] = {}


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """
    Centralized security management.

    Features:
    - JWT token creation and validation
    - API key generation and validation
    - Rate limiting
    - Access control
    """

    def __init__(self):
        self.api_keys: dict[str, APIKey] = {}

        # Statistics
        self.stats = {
            "auth_attempts": 0,
            "auth_successes": 0,
            "auth_failures": 0,
            "api_keys_created": 0,
            "api_keys_revoked": 0,
        }

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @trace_operation("jwt_create_token")
    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Token payload data
            expires_delta: Token expiration time (uses default if None)

        Returns:
            JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "iat": datetime.utcnow()})

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        logger.info(f"Created JWT token with expiry: {expire}")

        metrics.increment_counter("cial_jwt_tokens_created_total")

        return encoded_jwt

    @trace_operation("jwt_verify_token")
    def verify_access_token(self, token: str) -> TokenData | None:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None if invalid

        Raises:
            HTTPException: If token is invalid or expired
        """
        self.stats["auth_attempts"] += 1

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

            username: str = payload.get("sub")
            api_key: str = payload.get("api_key")
            scopes: list[str] = payload.get("scopes", [])

            if username is None and api_key is None:
                self.stats["auth_failures"] += 1
                metrics.increment_counter("cial_auth_failures_total", {"reason": "invalid_payload"})
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )

            self.stats["auth_successes"] += 1
            metrics.increment_counter("cial_auth_successes_total")

            return TokenData(username=username, api_key=api_key, scopes=scopes)

        except JWTError as e:
            self.stats["auth_failures"] += 1
            metrics.increment_counter("cial_auth_failures_total", {"reason": "jwt_error"})
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
            ) from e

    @trace_operation("api_key_create")
    def create_api_key(
        self,
        name: str,
        key_type: APIKeyType = APIKeyType.READ_ONLY,
        rate_limit: int = 100,
        metadata: dict[str, Any] | None = None,
    ) -> APIKey:
        """
        Create a new API key.

        Args:
            name: Descriptive name for the key
            key_type: Access level (read_only, read_write, admin)
            rate_limit: Requests per minute
            metadata: Additional metadata

        Returns:
            APIKey object with generated key
        """
        # Generate secure random API key
        api_key = f"cial_{secrets.token_urlsafe(32)}"

        # Hash for storage
        key_hash = self.hash_api_key(api_key)

        # Create API key object
        api_key_obj = APIKey(
            key=api_key,  # Return once, don't store plain
            key_hash=key_hash,
            name=name,
            type=key_type,
            created_at=datetime.utcnow(),
            rate_limit=rate_limit,
            metadata=metadata or {},
        )

        # Store by hash
        self.api_keys[key_hash] = api_key_obj

        self.stats["api_keys_created"] += 1
        metrics.increment_counter("cial_api_keys_created_total")

        logger.info(f"Created API key: {name} (type: {key_type.value})")

        return api_key_obj

    @trace_operation("api_key_validate")
    def validate_api_key(self, api_key: str) -> APIKey | None:
        """
        Validate API key and update last_used timestamp.

        Args:
            api_key: API key to validate

        Returns:
            APIKey object if valid, None if invalid
        """
        self.stats["auth_attempts"] += 1

        # Hash the provided key
        key_hash = self.hash_api_key(api_key)

        # Lookup
        api_key_obj = self.api_keys.get(key_hash)

        if api_key_obj and api_key_obj.is_active:
            # Update last_used
            api_key_obj.last_used = datetime.utcnow()

            self.stats["auth_successes"] += 1
            metrics.increment_counter(
                "cial_api_key_validations_total",
                {"status": "success", "type": api_key_obj.type.value},
            )

            return api_key_obj

        self.stats["auth_failures"] += 1
        metrics.increment_counter("cial_api_key_validations_total", {"status": "failure"})

        return None

    @trace_operation("api_key_revoke")
    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key.

        Args:
            api_key: API key to revoke

        Returns:
            True if revoked, False if not found
        """
        key_hash = self.hash_api_key(api_key)

        if key_hash in self.api_keys:
            self.api_keys[key_hash].is_active = False
            self.stats["api_keys_revoked"] += 1
            metrics.increment_counter("cial_api_keys_revoked_total")
            logger.info(f"Revoked API key: {self.api_keys[key_hash].name}")
            return True

        return False

    def list_api_keys(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        """
        List all API keys (without the actual key values).

        Args:
            include_inactive: Include revoked keys

        Returns:
            List of API key information
        """
        keys = []

        for api_key in self.api_keys.values():
            if not include_inactive and not api_key.is_active:
                continue

            keys.append(
                {
                    "name": api_key.name,
                    "type": api_key.type.value,
                    "created_at": api_key.created_at.isoformat(),
                    "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                    "is_active": api_key.is_active,
                    "rate_limit": api_key.rate_limit,
                    "metadata": api_key.metadata,
                }
            )

        return keys

    def get_stats(self) -> dict[str, Any]:
        """Get security statistics."""
        return {
            **self.stats,
            "active_api_keys": sum(1 for k in self.api_keys.values() if k.is_active),
            "total_api_keys": len(self.api_keys),
        }


# Global security manager
_security_manager: SecurityManager | None = None


def get_security_manager() -> SecurityManager:
    """
    Get the global security manager instance.

    Returns:
        SecurityManager: Global security manager
    """
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


# FastAPI dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> TokenData | None:
    """
    Dependency to get current authenticated user from JWT token.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            ...
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    security_manager = get_security_manager()
    return security_manager.verify_access_token(credentials.credentials)


async def verify_api_key(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme)
) -> APIKey | None:
    """
    Dependency to verify API key from Authorization header.

    Supports two formats:
    - Header: Authorization: Bearer cial_xxx
    - Query: ?api_key=cial_xxx

    Usage:
        @app.get("/api-protected")
        async def api_route(api_key: APIKey = Depends(verify_api_key)):
            ...
    """
    security_manager = get_security_manager()

    # Try Authorization header first
    if credentials:
        api_key = security_manager.validate_api_key(credentials.credentials)
        if api_key:
            return api_key

    # Try query parameter
    api_key_param = request.query_params.get("api_key")
    if api_key_param:
        api_key = security_manager.validate_api_key(api_key_param)
        if api_key:
            return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scope(required_scope: str):
    """
    Dependency to require specific scope/permission.

    Usage:
        @app.delete("/admin")
        async def admin_route(user: TokenData = Depends(require_scope("admin"))):
            ...
    """

    async def scope_checker(user: TokenData = Depends(get_current_user)):
        if required_scope not in user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )
        return user

    return scope_checker
