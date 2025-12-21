"""
CIAL System & Resilience API
Endpoints for system health, resilience metrics, and monitoring

Version: 1.0 - Production Monitoring
"""

import time
from datetime import datetime

from api.models.responses import APIVersion, VersionedResponse, success_response
from fastapi import APIRouter, Request
from infrastructure.logging_config import logger
from infrastructure.resilience import get_resilience_stats

router = APIRouter(prefix="/system", tags=["System & Monitoring"])


@router.get("/health", response_model=VersionedResponse)
async def health_check(request: Request):
    """
    System health check endpoint.

    Returns overall system health including:
    - API status
    - Timestamp
    - Version information

    Example Response:
    ```json
    {
        "version": "1.0",
        "status": "success",
        "data": {
            "status": "healthy",
            "timestamp": "2025-01-15T12:00:00Z",
            "api_version": "1.0.0"
        }
    }
    ```
    """
    start_time = time.time()

    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "api_version": "1.0.0",
        "uptime_check": "ok",
    }

    metadata = {
        "request_id": str(id(request)),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "path": str(request.url.path),
        "method": request.method,
    }

    return success_response(data=health_data, version=APIVersion.V1, metadata=metadata)


@router.get("/resilience", response_model=VersionedResponse)
async def get_resilience_metrics(request: Request):
    """
    Get comprehensive resilience metrics.

    Returns metrics for all resilience patterns:
    - Circuit Breakers (state, failure counts, thresholds)
    - Bulkheads (active requests, rejection rates)
    - Health Checks (reliability scores, success rates)

    This endpoint is crucial for:
    - SLA monitoring
    - Detecting degraded services
    - Capacity planning
    - Performance optimization

    Example Response:
    ```json
    {
        "version": "1.0",
        "status": "success",
        "data": {
            "circuit_breakers": {
                "coingecko_api": {
                    "state": "closed",
                    "fail_count": 0,
                    "fail_max": 3,
                    "timeout_duration": 30
                }
            },
            "bulkheads": {
                "postgres_writes": {
                    "name": "postgres_writes",
                    "max_concurrent": 20,
                    "active_count": 3,
                    "total_requests": 1250,
                    "rejected_requests": 0,
                    "rejection_rate": 0.0
                }
            },
            "health_checks": {
                "coingecko_api": {
                    "status": "healthy",
                    "success_rate": 0.98,
                    "reliability_score": 0.97,
                    "avg_response_time_ms": 145.3
                }
            }
        }
    }
    ```
    """
    start_time = time.time()

    try:
        # Get resilience statistics from all components
        resilience_data = get_resilience_stats()

        # Add summary statistics
        summary = {
            "total_circuit_breakers": len(resilience_data.get("circuit_breakers", {})),
            "total_bulkheads": len(resilience_data.get("bulkheads", {})),
            "total_health_checks": len(resilience_data.get("health_checks", {})),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Count circuit breaker states
        cb_states = {"closed": 0, "open": 0, "half_open": 0}
        for _cb_name, cb_data in resilience_data.get("circuit_breakers", {}).items():
            state = cb_data.get("state", "").lower()
            if "closed" in state:
                cb_states["closed"] += 1
            elif "open" in state and "half" not in state:
                cb_states["open"] += 1
            elif "half_open" in state or "half-open" in state:
                cb_states["half_open"] += 1

        summary["circuit_breaker_states"] = cb_states

        # Count healthy vs unhealthy services
        health_status = {"healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0}
        for _health_name, health_data in resilience_data.get("health_checks", {}).items():
            status = health_data.get("status", "unknown").lower()
            health_status[status] = health_status.get(status, 0) + 1

        summary["health_status_distribution"] = health_status

        # Calculate overall system health score
        total_health_checks = len(resilience_data.get("health_checks", {}))
        if total_health_checks > 0:
            overall_reliability = (
                sum(
                    health_data.get("reliability_score", 0.0)
                    for health_data in resilience_data.get("health_checks", {}).values()
                )
                / total_health_checks
            )
            summary["overall_reliability_score"] = round(overall_reliability, 3)
        else:
            summary["overall_reliability_score"] = 1.0

        # Add summary to response
        resilience_data["summary"] = summary

        metadata = {
            "request_id": str(id(request)),
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            "path": str(request.url.path),
            "method": request.method,
        }

        logger.info(
            "Resilience metrics retrieved",
            circuit_breakers=summary["total_circuit_breakers"],
            bulkheads=summary["total_bulkheads"],
            health_checks=summary["total_health_checks"],
            overall_reliability=summary["overall_reliability_score"],
        )

        return success_response(data=resilience_data, version=APIVersion.V1, metadata=metadata)

    except Exception as e:
        logger.error(f"Failed to get resilience metrics: {e}", exc_info=True)
        raise


@router.get("/resilience/circuit-breakers", response_model=VersionedResponse)
async def get_circuit_breakers(request: Request):
    """
    Get circuit breaker metrics only.

    Returns detailed metrics for all circuit breakers:
    - Current state (closed/open/half-open)
    - Failure counts
    - Thresholds
    - Timeout durations

    Use this endpoint to:
    - Monitor service availability
    - Detect cascade failures
    - Trigger alerts when circuits open
    """
    start_time = time.time()

    stats = get_resilience_stats()
    circuit_breakers = stats.get("circuit_breakers", {})

    metadata = {
        "request_id": str(id(request)),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "count": len(circuit_breakers),
    }

    return success_response(data=circuit_breakers, version=APIVersion.V1, metadata=metadata)


@router.get("/resilience/bulkheads", response_model=VersionedResponse)
async def get_bulkheads(request: Request):
    """
    Get bulkhead metrics only.

    Returns detailed metrics for all bulkheads:
    - Active concurrent requests
    - Total requests processed
    - Rejection counts and rates
    - Configured limits

    Use this endpoint to:
    - Monitor resource utilization
    - Detect capacity issues
    - Optimize concurrency limits
    """
    start_time = time.time()

    stats = get_resilience_stats()
    bulkheads = stats.get("bulkheads", {})

    metadata = {
        "request_id": str(id(request)),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "count": len(bulkheads),
    }

    return success_response(data=bulkheads, version=APIVersion.V1, metadata=metadata)


@router.get("/resilience/health", response_model=VersionedResponse)
async def get_health_checks(request: Request):
    """
    Get health check metrics only.

    Returns detailed health metrics for all services:
    - Health status (healthy/degraded/unhealthy)
    - Success/failure rates
    - Reliability scores (EMA-based)
    - Average response times
    - Last check timestamps

    Use this endpoint to:
    - Monitor SLA compliance
    - Detect degraded services
    - Trigger failover decisions
    - Generate health dashboards
    """
    start_time = time.time()

    stats = get_resilience_stats()
    health_checks = stats.get("health_checks", {})

    # Calculate aggregate metrics
    if health_checks:
        avg_reliability = sum(
            h.get("reliability_score", 0.0) for h in health_checks.values()
        ) / len(health_checks)

        avg_success_rate = sum(h.get("success_rate", 0.0) for h in health_checks.values()) / len(
            health_checks
        )

        aggregate = {
            "total_services": len(health_checks),
            "average_reliability_score": round(avg_reliability, 3),
            "average_success_rate": round(avg_success_rate, 3),
            "timestamp": datetime.utcnow().isoformat(),
        }
    else:
        aggregate = {
            "total_services": 0,
            "average_reliability_score": 1.0,
            "average_success_rate": 1.0,
            "timestamp": datetime.utcnow().isoformat(),
        }

    response_data = {"services": health_checks, "aggregate": aggregate}

    metadata = {
        "request_id": str(id(request)),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "count": len(health_checks),
    }

    return success_response(data=response_data, version=APIVersion.V1, metadata=metadata)


@router.get("/metrics", response_model=VersionedResponse)
async def get_system_metrics(request: Request):
    """
    Get comprehensive system metrics.

    Combines:
    - Resilience metrics
    - Performance metrics
    - Resource utilization

    This is the primary endpoint for monitoring dashboards.
    """
    start_time = time.time()

    resilience_stats = get_resilience_stats()

    # Build comprehensive metrics
    metrics = {
        "resilience": resilience_stats,
        "system": {"timestamp": datetime.utcnow().isoformat(), "api_version": "1.0.0"},
    }

    metadata = {
        "request_id": str(id(request)),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "path": str(request.url.path),
    }

    return success_response(data=metrics, version=APIVersion.V1, metadata=metadata)
