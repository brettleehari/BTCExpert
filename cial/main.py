"""
CIAL - Crypto Intelligence Abstraction Layer
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from datetime import datetime

from api.v1.intelligence import router as intelligence_router
from api.v1.agents import router as agents_router
from api.v1.memory import router as memory_router
from api.v1.validation import router as validation_router
from infrastructure.logging_config import logger
from infrastructure.config import settings
from core.service_registry import initialize_default_connectors
from infrastructure.redis_manager import get_redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("🚀 CIAL is starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")

    # Initialize infrastructure components
    # Initialize default data connectors
    initialize_default_connectors()
    logger.info("Default connectors initialized")

    # Initialize Redis connection (STM)
    try:
        redis_manager = get_redis_manager()
        redis_manager.connect()
        logger.info("✅ Redis (STM) connected successfully")
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}. STM will not be available.")

    # TODO: Initialize PostgreSQL connection
    # TODO: Initialize Kafka producer/consumer

    yield

    # Shutdown
    logger.info("🛑 CIAL is shutting down...")

    # Close Redis connection
    try:
        redis_manager = get_redis_manager()
        redis_manager.disconnect()
        logger.info("Redis disconnected")
    except:
        pass

    # TODO: Close PostgreSQL connection
    # TODO: Close Kafka connections


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

    Returns:
        dict: Service health status and component checks
    """
    # Check Redis connection
    redis_status = "disconnected"
    try:
        redis_manager = get_redis_manager()
        if redis_manager.is_connected():
            redis_status = "connected"
    except:
        pass

    return {
        "status": "healthy",
        "service": "CIAL",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "operational",
            "redis": redis_status,
            "postgres": "pending",
            "kafka": "pending",
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
            "intelligence": "/api/v1/intelligence",
            "agents": "/api/v1/agents",
            "memory": "/api/v1/memory",
            "validation": "/api/v1/validation"
        }
    }


# Register API routers
app.include_router(intelligence_router, prefix="/api/v1/intelligence", tags=["Intelligence"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(memory_router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(validation_router, prefix="/api/v1/validation", tags=["Validation"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
