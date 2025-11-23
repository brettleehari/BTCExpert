"""
CIAL Logging Configuration
Structured logging using structlog
"""

import structlog
import logging
import sys
from typing import Any


def setup_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """
    Configure structured logging for CIAL.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured structlog logger
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if log_level != "DEBUG"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


# Initialize logger
logger = setup_logging()


def log_api_request(method: str, path: str, **kwargs: Any) -> None:
    """Log API request with structured data."""
    logger.info(
        "api_request",
        method=method,
        path=path,
        **kwargs
    )


def log_api_response(status_code: int, duration: float, **kwargs: Any) -> None:
    """Log API response with structured data."""
    logger.info(
        "api_response",
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        **kwargs
    )


def log_intelligence_event(event_type: str, source: str, **kwargs: Any) -> None:
    """Log intelligence event with structured data."""
    logger.info(
        "intelligence_event",
        event_type=event_type,
        source=source,
        **kwargs
    )


def log_agent_activity(agent_id: str, action: str, **kwargs: Any) -> None:
    """Log agent activity with structured data."""
    logger.info(
        "agent_activity",
        agent_id=agent_id,
        action=action,
        **kwargs
    )
