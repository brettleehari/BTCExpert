"""
CIAL Resilience Patterns
Enterprise-grade resilience utilities for production SLA

Implements:
- Circuit Breaker Pattern (prevents cascade failures)
- Retry Pattern with Exponential Backoff (handles transient failures)
- Timeout Pattern (prevents hanging requests)
- Bulkhead Pattern (resource isolation)
- Health Check Pattern (continuous monitoring)

Design: Follows Netflix Hystrix patterns for microservice resilience
Version: 1.0 - Production Ready
"""

from typing import Callable, Any, Optional, Dict, TypeVar, ParamSpec
from functools import wraps
import asyncio
import time
import logging
from datetime import datetime, timedelta
from enum import Enum
import pybreaker
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
from infrastructure.logging_config import logger

P = ParamSpec('P')
T = TypeVar('T')


# ============================================================================
# CIRCUIT BREAKER PATTERN
# ============================================================================

class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreakerConfig:
    """
    Circuit breaker configuration.

    Based on Netflix Hystrix recommendations:
    - fail_max: 5 failures in 60 seconds
    - timeout: 60 seconds before retry
    - expected_exception: What counts as a failure

    Example:
        config = CircuitBreakerConfig(
            fail_max=5,
            timeout_duration=60,
            name="coingecko_api"
        )
    """

    def __init__(
        self,
        fail_max: int = 5,
        timeout_duration: int = 60,
        name: str = "default",
        expected_exception: type = Exception
    ):
        self.fail_max = fail_max
        self.timeout_duration = timeout_duration
        self.name = name
        self.expected_exception = expected_exception


# Global circuit breakers registry
_circuit_breakers: Dict[str, pybreaker.CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> pybreaker.CircuitBreaker:
    """
    Get or create a circuit breaker.

    Args:
        name: Circuit breaker identifier
        config: Configuration (created with defaults if None)

    Returns:
        CircuitBreaker instance

    Example:
        breaker = get_circuit_breaker("coingecko_api")

        @breaker
        async def fetch_price():
            return await api.get_price()
    """
    if name not in _circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig(name=name)

        breaker = pybreaker.CircuitBreaker(
            fail_max=config.fail_max,
            timeout_duration=config.timeout_duration,
            expected_exception=config.expected_exception,
            name=config.name,
            listeners=[_CircuitBreakerListener()]
        )
        _circuit_breakers[name] = breaker
        logger.info(f"Circuit breaker created: {name}", fail_max=config.fail_max, timeout=config.timeout_duration)

    return _circuit_breakers[name]


class _CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Custom listener for circuit breaker events"""

    def state_change(self, cb, old_state, new_state):
        """Log state changes"""
        logger.warning(
            f"Circuit breaker state change: {cb.name}",
            old_state=str(old_state),
            new_state=str(new_state),
            failure_count=cb.fail_counter
        )

    def failure(self, cb, exc):
        """Log failures"""
        logger.error(
            f"Circuit breaker failure: {cb.name}",
            exception=str(exc),
            failure_count=cb.fail_counter,
            state=str(cb.current_state)
        )

    def success(self, cb):
        """Log successes (only in half-open state)"""
        if cb.current_state == pybreaker.STATE_HALF_OPEN:
            logger.info(f"Circuit breaker success: {cb.name}", state="half_open")


def circuit_breaker(
    name: str,
    fail_max: int = 5,
    timeout_duration: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator to add circuit breaker to a function.

    Args:
        name: Circuit breaker identifier
        fail_max: Number of failures before opening circuit
        timeout_duration: Seconds to wait before half-open
        expected_exception: Exception type that triggers circuit

    Example:
        @circuit_breaker("coingecko_api", fail_max=3, timeout_duration=30)
        async def fetch_price(symbol: str):
            return await api.get_price(symbol)

        # After 3 failures, circuit opens for 30 seconds
        # Calls during open state fail immediately (fast-fail)
    """
    config = CircuitBreakerConfig(
        fail_max=fail_max,
        timeout_duration=timeout_duration,
        name=name,
        expected_exception=expected_exception
    )
    breaker = get_circuit_breaker(name, config)
    return breaker


# ============================================================================
# RETRY PATTERN WITH EXPONENTIAL BACKOFF
# ============================================================================

def retry_with_backoff(
    max_attempts: int = 5,
    min_wait: int = 1,
    max_wait: int = 60,
    multiplier: int = 2,
    exceptions: tuple = (Exception,),
    logger_instance = None
):
    """
    Decorator for retry with exponential backoff.

    Implements exponential backoff: wait = min(max_wait, min_wait * (multiplier ^ attempt))

    Args:
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Backoff multiplier
        exceptions: Tuple of exceptions to retry on
        logger_instance: Logger for retry events

    Example:
        @retry_with_backoff(max_attempts=5, min_wait=2, max_wait=30)
        async def store_in_database(data):
            await db.insert(data)

        # Retry schedule: 2s, 4s, 8s, 16s, 30s (capped at max_wait)

    Benefits:
        - Handles transient failures (network blips, temporary outages)
        - Exponential backoff prevents overwhelming recovering services
        - Configurable per use case (DB vs API vs Cache)
    """
    log = logger_instance or logger

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=multiplier,
            min=min_wait,
            max=max_wait
        ),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(log, logging.WARNING),
        after=after_log(log, logging.INFO),
        reraise=True
    )


# ============================================================================
# TIMEOUT PATTERN
# ============================================================================

class TimeoutError(Exception):
    """Raised when operation times out"""
    pass


def timeout(seconds: float):
    """
    Decorator to add timeout to async functions.

    Args:
        seconds: Timeout in seconds

    Example:
        @timeout(5.0)
        async def fetch_data():
            return await slow_api.get_data()

        # Raises TimeoutError if takes > 5 seconds

    Benefits:
        - Prevents hanging requests that consume resources
        - Ensures predictable response times for SLA
        - Critical for maintaining system responsiveness
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Function timeout: {func.__name__}",
                    timeout_seconds=seconds
                )
                raise TimeoutError(f"{func.__name__} timed out after {seconds}s")
        return wrapper
    return decorator


# ============================================================================
# BULKHEAD PATTERN (Resource Isolation)
# ============================================================================

class Bulkhead:
    """
    Bulkhead pattern for resource isolation.

    Limits concurrent operations to prevent resource exhaustion.
    Named after ship bulkheads that contain flooding.

    Example:
        # Only allow 10 concurrent database writes
        db_bulkhead = Bulkhead(max_concurrent=10, name="database_writes")

        async with db_bulkhead:
            await db.write(data)

        # 11th concurrent call will wait until a slot opens

    Benefits:
        - Prevents one component from exhausting all resources
        - Isolates failures (one slow operation doesn't block others)
        - Enables fine-grained resource control per service
    """

    def __init__(self, max_concurrent: int, name: str = "default", timeout: Optional[float] = None):
        """
        Create a bulkhead.

        Args:
            max_concurrent: Maximum concurrent operations
            name: Bulkhead identifier
            timeout: Optional timeout when waiting for slot (seconds)
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.name = name
        self.timeout = timeout
        self._active_count = 0
        self._total_requests = 0
        self._rejected_requests = 0

        logger.info(f"Bulkhead created: {name}", max_concurrent=max_concurrent)

    async def __aenter__(self):
        """Acquire slot"""
        self._total_requests += 1

        try:
            if self.timeout:
                await asyncio.wait_for(
                    self.semaphore.acquire(),
                    timeout=self.timeout
                )
            else:
                await self.semaphore.acquire()

            self._active_count += 1
            logger.debug(
                f"Bulkhead slot acquired: {self.name}",
                active=self._active_count,
                max=self.max_concurrent
            )
        except asyncio.TimeoutError:
            self._rejected_requests += 1
            logger.error(
                f"Bulkhead timeout: {self.name}",
                active=self._active_count,
                rejected=self._rejected_requests
            )
            raise TimeoutError(f"Bulkhead {self.name} timeout - too many concurrent operations")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release slot"""
        self._active_count -= 1
        self.semaphore.release()
        logger.debug(
            f"Bulkhead slot released: {self.name}",
            active=self._active_count
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get bulkhead statistics"""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active_count": self._active_count,
            "total_requests": self._total_requests,
            "rejected_requests": self._rejected_requests,
            "rejection_rate": self._rejected_requests / max(self._total_requests, 1)
        }


# Global bulkheads registry
_bulkheads: Dict[str, Bulkhead] = {}


def get_bulkhead(name: str, max_concurrent: int = 10, timeout: Optional[float] = None) -> Bulkhead:
    """
    Get or create a bulkhead.

    Args:
        name: Bulkhead identifier
        max_concurrent: Maximum concurrent operations
        timeout: Optional timeout when waiting for slot

    Returns:
        Bulkhead instance

    Example:
        db_bulkhead = get_bulkhead("database", max_concurrent=20)

        async with db_bulkhead:
            await db.execute(query)
    """
    if name not in _bulkheads:
        _bulkheads[name] = Bulkhead(max_concurrent, name, timeout)
    return _bulkheads[name]


# ============================================================================
# HEALTH CHECK PATTERN
# ============================================================================

class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """
    Health check for monitoring service availability.

    Tracks:
    - Success/failure counts
    - Response times
    - Last check timestamp
    - Exponential moving average for reliability scoring

    Example:
        health = HealthCheck(name="coingecko_api")

        try:
            result = await api.get_price()
            health.record_success(response_time_ms=125)
        except Exception as e:
            health.record_failure(error=str(e))

        if health.is_healthy():
            # Use the service
        else:
            # Use fallback/cache
    """

    def __init__(self, name: str, threshold_success_rate: float = 0.8):
        """
        Create a health check.

        Args:
            name: Service identifier
            threshold_success_rate: Minimum success rate to be healthy (0.0-1.0)
        """
        self.name = name
        self.threshold_success_rate = threshold_success_rate

        # Counters
        self.success_count = 0
        self.failure_count = 0
        self.total_requests = 0

        # Timing
        self.last_success: Optional[datetime] = None
        self.last_failure: Optional[datetime] = None
        self.last_check: Optional[datetime] = None

        # Response times (for SLA monitoring)
        self.avg_response_time_ms: float = 0.0
        self.max_response_time_ms: float = 0.0

        # Exponential moving average for reliability
        self.reliability_score: float = 1.0  # Start optimistic
        self.ema_alpha: float = 0.2  # Weight for new values

    def record_success(self, response_time_ms: float = 0.0):
        """Record successful request"""
        self.success_count += 1
        self.total_requests += 1
        self.last_success = datetime.utcnow()
        self.last_check = datetime.utcnow()

        # Update response time metrics
        if response_time_ms > 0:
            if self.avg_response_time_ms == 0:
                self.avg_response_time_ms = response_time_ms
            else:
                # Exponential moving average
                self.avg_response_time_ms = (
                    self.ema_alpha * response_time_ms +
                    (1 - self.ema_alpha) * self.avg_response_time_ms
                )

            self.max_response_time_ms = max(self.max_response_time_ms, response_time_ms)

        # Update reliability score (increase on success)
        self.reliability_score = min(
            1.0,
            self.reliability_score * 0.95 + 0.05  # Slowly increase to 1.0
        )

        logger.debug(f"Health check success: {self.name}", reliability=self.reliability_score)

    def record_failure(self, error: str = ""):
        """Record failed request"""
        self.failure_count += 1
        self.total_requests += 1
        self.last_failure = datetime.utcnow()
        self.last_check = datetime.utcnow()

        # Update reliability score (decrease on failure)
        self.reliability_score = max(
            0.0,
            self.reliability_score * 0.9  # Rapidly decrease
        )

        logger.warning(
            f"Health check failure: {self.name}",
            error=error,
            reliability=self.reliability_score
        )

    def get_status(self) -> HealthStatus:
        """Get current health status"""
        if self.total_requests == 0:
            return HealthStatus.UNKNOWN

        success_rate = self.success_count / self.total_requests

        if success_rate >= self.threshold_success_rate:
            return HealthStatus.HEALTHY
        elif success_rate >= self.threshold_success_rate * 0.5:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        return self.get_status() == HealthStatus.HEALTHY

    def get_stats(self) -> Dict[str, Any]:
        """Get detailed health statistics"""
        success_rate = (
            self.success_count / self.total_requests
            if self.total_requests > 0
            else 0.0
        )

        return {
            "name": self.name,
            "status": self.get_status().value,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_requests": self.total_requests,
            "success_rate": success_rate,
            "reliability_score": self.reliability_score,
            "avg_response_time_ms": self.avg_response_time_ms,
            "max_response_time_ms": self.max_response_time_ms,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_check": self.last_check.isoformat() if self.last_check else None
        }

    def reset(self):
        """Reset health check statistics"""
        self.success_count = 0
        self.failure_count = 0
        self.total_requests = 0
        self.reliability_score = 1.0
        self.avg_response_time_ms = 0.0
        self.max_response_time_ms = 0.0
        logger.info(f"Health check reset: {self.name}")


# Global health checks registry
_health_checks: Dict[str, HealthCheck] = {}


def get_health_check(name: str, threshold_success_rate: float = 0.8) -> HealthCheck:
    """
    Get or create a health check.

    Args:
        name: Service identifier
        threshold_success_rate: Minimum success rate to be healthy

    Returns:
        HealthCheck instance

    Example:
        health = get_health_check("coingecko_api", threshold_success_rate=0.9)

        try:
            data = await api.fetch()
            health.record_success(response_time_ms=100)
        except Exception as e:
            health.record_failure(error=str(e))
    """
    if name not in _health_checks:
        _health_checks[name] = HealthCheck(name, threshold_success_rate)
    return _health_checks[name]


# ============================================================================
# RESILIENCE STATISTICS
# ============================================================================

def get_resilience_stats() -> Dict[str, Any]:
    """
    Get statistics for all resilience components.

    Returns:
        Dict with circuit breakers, bulkheads, and health checks

    Example:
        stats = get_resilience_stats()
        print(f"Circuit breakers: {len(stats['circuit_breakers'])}")
        print(f"Bulkheads: {len(stats['bulkheads'])}")
        print(f"Health checks: {len(stats['health_checks'])}")
    """
    return {
        "circuit_breakers": {
            name: {
                "state": str(cb.current_state),
                "fail_count": cb.fail_counter,
                "fail_max": cb.fail_max,
                "timeout_duration": cb.timeout_duration
            }
            for name, cb in _circuit_breakers.items()
        },
        "bulkheads": {
            name: bulkhead.get_stats()
            for name, bulkhead in _bulkheads.items()
        },
        "health_checks": {
            name: health.get_stats()
            for name, health in _health_checks.items()
        }
    }
