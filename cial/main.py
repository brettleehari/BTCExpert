"""
CIAL - Crypto Intelligence Abstraction Layer
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
import time
from datetime import datetime

from api.v1.intelligence import router as intelligence_router
from api.v1.agents import router as agents_router
from api.v1.memory import router as memory_router
from api.v1.validation import router as validation_router
from api.v1.system import router as system_router
from api.v1.timeseries import router as timeseries_router
from infrastructure.logging_config import logger
from infrastructure.config import settings
from core.service_registry import initialize_default_connectors
from infrastructure.container import initialize_container, shutdown_container, get_container
from infrastructure.observability import (
    initialize_observability,
    get_prometheus_metrics,
    sync_resilience_metrics
)
from prometheus_client import CONTENT_TYPE_LATEST


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    Uses DI container for centralized dependency management.
    """
    # Startup
    logger.info("🚀 CIAL is starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")

    # Initialize observability FIRST (before other components)
    initialize_observability(app)
    logger.info("✅ Observability stack initialized")

    # Initialize DI container (manages all dependencies)
    await initialize_container()
    logger.info("✅ DI Container initialized")

    # Initialize default data connectors
    initialize_default_connectors()
    logger.info("✅ Default connectors initialized")

    logger.info("🎉 CIAL startup complete - Ready to serve requests!")

    yield

    # Shutdown
    logger.info("🛑 CIAL is shutting down...")

    # Shutdown DI container (releases all resources)
    await shutdown_container()

    logger.info("👋 CIAL shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="CIAL - Crypto Intelligence Abstraction Layer",
    description="AI-powered crypto market intelligence platform for agentic trading systems",
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify service status.

    Uses DI container to check component health.

    Returns:
        dict: Service health status and component checks
    """
    container = get_container()

    # Check Redis connection
    redis_status = "disconnected"
    try:
        redis_manager = container.redis_manager()
        if redis_manager.is_connected():
            redis_status = "connected"
    except:
        pass

    # Check Kafka connection
    kafka_status = "disconnected"
    try:
        kafka_manager = container.kafka_manager()
        if kafka_manager.is_connected():
            kafka_status = "connected"
    except:
        pass

    # Check PostgreSQL connection
    postgres_status = "disconnected"
    try:
        postgres_manager = container.postgres_manager()
        if postgres_manager.is_connected():
            postgres_status = "connected"
    except:
        pass

    return {
        "status": "healthy",
        "service": "CIAL",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "dependency_injection": "enabled",
        "components": {
            "api": "operational",
            "redis": redis_status,
            "postgres": postgres_status,
            "kafka": kafka_status,
        }
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: API welcome message and documentation links
    """
    return {
        "message": "Welcome to CIAL - Crypto Intelligence Abstraction Layer",
        "tagline": "The Neural Network for Crypto Data Intelligence",
        "version": settings.API_VERSION,
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/api/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "intelligence": "/api/v1/intelligence",
            "agents": "/api/v1/agents",
            "memory": "/api/v1/memory",
            "validation": "/api/v1/validation",
            "system": "/api/v1/system",
            "resilience": "/api/v1/system/resilience",
            "timeseries": "/api/v1/timeseries"
        },
        "monitoring": {
            "prometheus_metrics": "/metrics",
            "resilience_stats": "/api/v1/system/resilience",
            "health_check": "/health"
        }
    }


# Prometheus metrics endpoint
@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns Prometheus-formatted metrics for:
    - Intelligence pipeline metrics
    - API request metrics
    - Circuit breaker states
    - Bulkhead utilization
    - Health scores
    - And all OpenTelemetry auto-instrumentation metrics

    This endpoint is consumed by Prometheus scraper.
    """
    # Sync resilience metrics before exporting
    sync_resilience_metrics()

    return Response(
        content=get_prometheus_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )


# Register API routers
app.include_router(intelligence_router, prefix="/api/v1/intelligence", tags=["Intelligence"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(memory_router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(validation_router, prefix="/api/v1/validation", tags=["Validation"])
app.include_router(system_router, prefix="/api/v1", tags=["System & Monitoring"])
app.include_router(timeseries_router, prefix="/api/v1", tags=["TimescaleDB Analytics"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
