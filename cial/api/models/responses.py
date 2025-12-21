"""
CIAL API Response Models
Versioned response wrappers for backward compatibility

Version: 2.0 - Migrated to Pydantic V2
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIVersion(str, Enum):
    """API version identifiers"""

    V1 = "1.0"
    V2 = "2.0"


class ResponseStatus(str, Enum):
    """Standard response status codes"""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PENDING = "pending"


class VersionedResponse(BaseModel, Generic[T]):
    """
    Generic versioned response wrapper for all API endpoints.

    Ensures consistent response format and enables version tracking.

    Example:
        {
            "version": "1.0",
            "status": "success",
            "data": {...},
            "metadata": {
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "abc123"
            }
        }
    """

    version: APIVersion = Field(
        default=APIVersion.V1, description="API version used for this response"
    )
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="Response status")
    data: T = Field(description="Response payload")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata (timestamp, request_id, etc.)"
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Error details if status is error or partial"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0",
                "status": "success",
                "data": {"result": "example"},
                "metadata": {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "request_id": "abc123",
                    "processing_time_ms": 45,
                },
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper for list endpoints.

    Example:
        {
            "version": "1.0",
            "status": "success",
            "data": [...],
            "pagination": {
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5
            }
        }
    """

    version: APIVersion = Field(default=APIVersion.V1, description="API version")
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="Response status")
    data: List[T] = Field(description="List of items")
    pagination: Dict[str, int] = Field(description="Pagination metadata")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0",
                "status": "success",
                "data": [],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5,
                    "has_next": True,
                    "has_previous": False,
                },
            }
        }
    )


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    Example:
        {
            "version": "1.0",
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": {...}
            },
            "metadata": {
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "abc123"
            }
        }
    """

    version: APIVersion = Field(default=APIVersion.V1, description="API version")
    status: ResponseStatus = Field(
        default=ResponseStatus.ERROR, description="Always 'error' for error responses"
    )
    error: Dict[str, Any] = Field(description="Error details")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0",
                "status": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {"field": "symbol", "error": "Required field missing"},
                },
                "metadata": {"timestamp": "2024-01-15T10:30:00Z", "request_id": "abc123"},
            }
        }
    )


# Response builder utilities


def success_response(
    data: Any, version: APIVersion = APIVersion.V1, metadata: Optional[Dict[str, Any]] = None
) -> VersionedResponse:
    """
    Build a successful versioned response.

    Args:
        data: Response payload
        version: API version
        metadata: Optional metadata

    Returns:
        VersionedResponse with success status
    """
    response_metadata = metadata or {}
    response_metadata["timestamp"] = datetime.utcnow().isoformat()

    return VersionedResponse(
        version=version, status=ResponseStatus.SUCCESS, data=data, metadata=response_metadata
    )


def error_response(
    error_code: str,
    error_message: str,
    details: Optional[Dict[str, Any]] = None,
    version: APIVersion = APIVersion.V1,
    metadata: Optional[Dict[str, Any]] = None,
) -> ErrorResponse:
    """
    Build an error response.

    Args:
        error_code: Error code identifier
        error_message: Human-readable error message
        details: Optional error details
        version: API version
        metadata: Optional metadata

    Returns:
        ErrorResponse with error details
    """
    response_metadata = metadata or {}
    response_metadata["timestamp"] = datetime.utcnow().isoformat()

    return ErrorResponse(
        version=version,
        status=ResponseStatus.ERROR,
        error={"code": error_code, "message": error_message, "details": details or {}},
        metadata=response_metadata,
    )


def paginated_response(
    data: List[Any],
    total: int,
    page: int,
    page_size: int,
    version: APIVersion = APIVersion.V1,
    metadata: Optional[Dict[str, Any]] = None,
) -> PaginatedResponse:
    """
    Build a paginated response.

    Args:
        data: List of items for current page
        total: Total number of items
        page: Current page number (1-indexed)
        page_size: Items per page
        version: API version
        metadata: Optional metadata

    Returns:
        PaginatedResponse with pagination metadata
    """
    response_metadata = metadata or {}
    response_metadata["timestamp"] = datetime.utcnow().isoformat()

    total_pages = (total + page_size - 1) // page_size  # Ceiling division

    return PaginatedResponse(
        version=version,
        status=ResponseStatus.SUCCESS,
        data=data,
        pagination={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
        metadata=response_metadata,
    )
