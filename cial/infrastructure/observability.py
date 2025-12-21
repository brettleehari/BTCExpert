"""
CIAL Observability Infrastructure
OpenTelemetry instrumentation, Prometheus metrics, and distributed tracing

Version: 1.0 - Production Monitoring Stack
"""

import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

# OpenTelemetry imports
from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Prometheus imports
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

from infrastructure.config import settings
from infrastructure.logging_config import logger

# ============================================================================
# OPENTELEMETRY SETUP
# ============================================================================

# Create resource with service information
resource = Resource.create(
    {
        SERVICE_NAME: "cial",
        SERVICE_VERSION: settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "deployment.name": "cial-production",
    }
)

# Global tracer and meter providers
_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_prometheus_reader: PrometheusMetricReader | None = None

# Global tracer and meter
tracer = None
meter = None


def initialize_observability(app=None) -> None:
    """
    Initialize OpenTelemetry observability stack.

    Sets up:
    - Distributed tracing with OpenTelemetry
    - Prometheus metrics export
    - Automatic instrumentation for FastAPI, HTTPX, Redis, SQLAlchemy

    Args:
        app: FastAPI application instance (optional, for automatic instrumentation)
    """
    global _tracer_provider, _meter_provider, _prometheus_reader, tracer, meter

    # ========================================================================
    # TRACING SETUP
    # ========================================================================

    # Create tracer provider with resource
    _tracer_provider = TracerProvider(resource=resource)

    # Add console span exporter for development
    if settings.DEBUG:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Get tracer
    tracer = trace.get_tracer(__name__)

    logger.info("OpenTelemetry tracing initialized")

    # ========================================================================
    # METRICS SETUP
    # ========================================================================

    # Create Prometheus metric reader
    _prometheus_reader = PrometheusMetricReader()

    # Create meter provider
    _meter_provider = MeterProvider(resource=resource, metric_readers=[_prometheus_reader])

    # Set global meter provider
    metrics.set_meter_provider(_meter_provider)

    # Get meter
    meter = metrics.get_meter(__name__)

    logger.info("Prometheus metrics initialized")

    # ========================================================================
    # AUTOMATIC INSTRUMENTATION
    # ========================================================================

    # Instrument FastAPI
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented for tracing")

    # Instrument HTTPX (for external API calls)
    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX instrumented for tracing")

    # Instrument Redis
    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumented for tracing")
    except Exception as e:
        logger.warning(f"Redis instrumentation failed: {e}")

    # Instrument SQLAlchemy
    try:
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumented for tracing")
    except Exception as e:
        logger.warning(f"SQLAlchemy instrumentation failed: {e}")

    logger.info("✅ Observability stack initialized successfully")


def get_prometheus_metrics() -> bytes:
    """
    Get Prometheus metrics in text format.

    Returns:
        bytes: Prometheus metrics in text exposition format

    Usage:
        @app.get("/metrics")
        async def metrics():
            return Response(
                content=get_prometheus_metrics(),
                media_type=CONTENT_TYPE_LATEST
            )
    """
    if _prometheus_reader is None:
        logger.warning("Prometheus reader not initialized")
        return b""

    # Generate Prometheus metrics
    return generate_latest()


# ============================================================================
# CUSTOM PROMETHEUS METRICS
# ============================================================================

# Intelligence Pipeline Metrics
intelligence_messages_total = Counter(
    "cial_intelligence_messages_total",
    "Total intelligence messages processed",
    ["type", "importance", "source"],
)

intelligence_processing_duration = Histogram(
    "cial_intelligence_processing_seconds",
    "Time spent processing intelligence messages",
    ["type", "source"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

intelligence_routing_total = Counter(
    "cial_intelligence_routing_total",
    "Total intelligence messages routed to agents",
    ["type", "agent_type"],
)

# Agent Metrics
agents_registered_total = Gauge(
    "cial_agents_registered_total", "Total number of registered agents", ["agent_type", "status"]
)

agent_messages_processed = Counter(
    "cial_agent_messages_processed_total",
    "Total messages processed by agents",
    ["agent_id", "agent_type"],
)

# Data Connector Metrics
connector_requests_total = Counter(
    "cial_connector_requests_total",
    "Total requests to data connectors",
    ["connector", "status"],  # status: success, failure
)

connector_response_duration = Histogram(
    "cial_connector_response_seconds",
    "Data connector response time",
    ["connector"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

connector_circuit_breaker_state = Gauge(
    "cial_connector_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["connector"],
)

# Memory Metrics
memory_stm_operations = Counter(
    "cial_memory_stm_operations_total",
    "Short-term memory operations",
    ["operation"],  # operation: get, set, delete
)

memory_ltm_operations = Counter(
    "cial_memory_ltm_operations_total",
    "Long-term memory operations",
    ["operation"],  # operation: store, retrieve, query
)

memory_cache_hits = Counter("cial_memory_cache_hits_total", "Cache hits in STM", ["key_type"])

memory_cache_misses = Counter("cial_memory_cache_misses_total", "Cache misses in STM", ["key_type"])

# API Metrics (supplementing FastAPI instrumentation)
api_requests_total = Counter(
    "cial_api_requests_total", "Total API requests", ["method", "endpoint", "status_code"]
)

api_request_duration = Histogram(
    "cial_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

api_active_requests = Gauge(
    "cial_api_active_requests", "Number of active API requests", ["endpoint"]
)

# Resilience Metrics (integrating with Session 13)
resilience_circuit_breaker_state = Gauge(
    "cial_resilience_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["circuit_name"],
)

resilience_circuit_breaker_failures = Counter(
    "cial_resilience_circuit_breaker_failures_total", "Circuit breaker failures", ["circuit_name"]
)

resilience_bulkhead_active = Gauge(
    "cial_resilience_bulkhead_active_requests", "Active requests in bulkhead", ["bulkhead_name"]
)

resilience_bulkhead_rejected = Counter(
    "cial_resilience_bulkhead_rejected_total", "Rejected requests from bulkhead", ["bulkhead_name"]
)

resilience_retry_attempts = Counter(
    "cial_resilience_retry_attempts_total",
    "Total retry attempts",
    ["operation", "result"],  # result: success, failure
)

resilience_health_score = Gauge(
    "cial_resilience_health_score", "Health check reliability score (0.0-1.0)", ["service"]
)

# System Metrics
system_info = Info("cial_system", "CIAL system information")

# Set system info
system_info.info(
    {
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": "3.11",
    }
)


# ============================================================================
# TRACING DECORATORS
# ============================================================================


def trace_operation(operation_name: str = None, attributes: dict[str, Any] = None):
    """
    Decorator to add distributed tracing to a function.

    Args:
        operation_name: Name of the operation (defaults to function name)
        attributes: Additional attributes to add to the span

    Example:
        @trace_operation("fetch_price", {"source": "coingecko"})
        async def get_price(symbol: str):
            return await fetch_price(symbol)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(op_name) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                # Add arguments as attributes (if not too many)
                if len(kwargs) <= 5:
                    for key, value in kwargs.items():
                        span.set_attribute(f"arg.{key}", str(value))

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("result.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("result.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(op_name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("result.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("result.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# METRIC HELPERS
# ============================================================================


def record_intelligence_message(
    intelligence_type: str, importance: str, source: str, processing_time: float
):
    """Record intelligence message metrics."""
    intelligence_messages_total.labels(
        type=intelligence_type, importance=importance, source=source
    ).inc()

    intelligence_processing_duration.labels(type=intelligence_type, source=source).observe(
        processing_time
    )


def record_connector_request(connector: str, success: bool, duration: float):
    """Record data connector request metrics."""
    status = "success" if success else "failure"

    connector_requests_total.labels(connector=connector, status=status).inc()

    connector_response_duration.labels(connector=connector).observe(duration)


def record_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record API request metrics."""
    api_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

    api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def update_circuit_breaker_state(circuit_name: str, state: str):
    """
    Update circuit breaker state metric.

    Args:
        circuit_name: Name of the circuit breaker
        state: State (closed, open, half-open)
    """
    state_map = {"closed": 0, "open": 1, "half_open": 2, "half-open": 2}
    state_value = state_map.get(state.lower().replace("_", "-"), 0)

    resilience_circuit_breaker_state.labels(circuit_name=circuit_name).set(state_value)


def update_bulkhead_metrics(bulkhead_name: str, active: int, rejected: int):
    """Update bulkhead metrics."""
    resilience_bulkhead_active.labels(bulkhead_name=bulkhead_name).set(active)


def update_health_score(service: str, score: float):
    """Update health score metric."""
    resilience_health_score.labels(service=service).set(score)


# ============================================================================
# OBSERVABILITY INTEGRATION
# ============================================================================


def sync_resilience_metrics():
    """
    Sync resilience metrics from Session 13 to Prometheus.

    Call this periodically (e.g., every 15 seconds) to update
    Prometheus metrics with current resilience state.
    """
    try:
        from infrastructure.resilience import get_resilience_stats

        stats = get_resilience_stats()

        # Update circuit breaker metrics
        for name, cb in stats.get("circuit_breakers", {}).items():
            state = cb.get("state", "unknown")
            update_circuit_breaker_state(name, state)

            # Record failures
            fail_count = cb.get("fail_count", 0)
            if fail_count > 0:
                resilience_circuit_breaker_failures.labels(circuit_name=name).inc(fail_count)

        # Update bulkhead metrics
        for name, bulkhead in stats.get("bulkheads", {}).items():
            active = bulkhead.get("active_count", 0)
            rejected = bulkhead.get("rejected_requests", 0)

            resilience_bulkhead_active.labels(bulkhead_name=name).set(active)

            if rejected > 0:
                resilience_bulkhead_rejected.labels(bulkhead_name=name).inc(rejected)

        # Update health scores
        for name, health in stats.get("health_checks", {}).items():
            score = health.get("reliability_score", 0.0)
            resilience_health_score.labels(service=name).set(score)

    except Exception as e:
        logger.error(f"Failed to sync resilience metrics: {e}")


# ============================================================================
# GRAFANA DASHBOARD CONFIGURATION
# ============================================================================


def get_grafana_dashboard_json() -> dict[str, Any]:
    """
    Get Grafana dashboard configuration for CIAL monitoring.

    Returns:
        Dict: Grafana dashboard JSON configuration
    """
    return {
        "dashboard": {
            "title": "CIAL - Crypto Intelligence Abstraction Layer",
            "tags": ["cial", "crypto", "intelligence"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "Intelligence Messages Processed",
                    "targets": [{"expr": "rate(cial_intelligence_messages_total[5m])"}],
                    "type": "graph",
                },
                {
                    "title": "Circuit Breaker States",
                    "targets": [{"expr": "cial_resilience_circuit_breaker_state"}],
                    "type": "stat",
                },
                {
                    "title": "API Request Duration (P95)",
                    "targets": [
                        {"expr": "histogram_quantile(0.95, cial_api_request_duration_seconds)"}
                    ],
                    "type": "graph",
                },
                {
                    "title": "Health Scores",
                    "targets": [{"expr": "cial_resilience_health_score"}],
                    "type": "gauge",
                },
            ],
        }
    }
