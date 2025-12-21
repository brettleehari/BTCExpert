"""
CIAL Dependency Injection Container
Centralized dependency management with lifecycle control

Version: 1.0 - Production-Ready DI Container
"""

from dependency_injector import containers, providers

from infrastructure.config import settings
from infrastructure.logging_config import logger


class ApplicationContainer(containers.DeclarativeContainer):
    """
    Main application container for dependency injection.

    Manages lifecycle of:
    - Infrastructure components (Redis, Kafka, PostgreSQL)
    - Core components (Broker, Registries)
    - Memory components (STM, LTM)
    - Connectors (CoinGecko)
    - Validators

    Benefits:
    - Single source of truth for dependencies
    - Proper lifecycle management (startup/shutdown)
    - Easy testing with mock providers
    - Clear dependency graph
    - No hidden global state
    """

    # Configuration
    config = providers.Singleton(lambda: settings)

    # ========================================================================
    # INFRASTRUCTURE LAYER
    # ========================================================================

    # Redis Manager (Short-Term Memory)
    redis_manager = providers.Singleton(
        lambda: __import__("infrastructure.redis_manager", fromlist=["RedisManager"]).RedisManager()
    )

    # Kafka Manager (Event Stream)
    kafka_manager = providers.Singleton(
        lambda: __import__("infrastructure.kafka_manager", fromlist=["KafkaManager"]).KafkaManager()
    )

    # PostgreSQL Manager (Long-Term Memory)
    postgres_manager = providers.Singleton(
        lambda: __import__(
            "infrastructure.postgres_manager", fromlist=["PostgresManager"]
        ).PostgresManager()
    )

    # ========================================================================
    # MEMORY LAYER
    # ========================================================================

    # Short-Term Memory
    short_term_memory = providers.Singleton(
        lambda redis_mgr: __import__(
            "memory.short_term_memory", fromlist=["ShortTermMemory"]
        ).ShortTermMemory(redis_mgr),
        redis_mgr=redis_manager,
    )

    # Long-Term Memory
    long_term_memory = providers.Singleton(
        lambda postgres_mgr: __import__(
            "memory.long_term_memory", fromlist=["LongTermMemory"]
        ).LongTermMemory(postgres_mgr),
        postgres_mgr=postgres_manager,
    )

    # ========================================================================
    # CORE LAYER
    # ========================================================================

    # Agent Registry
    agent_registry = providers.Singleton(
        lambda: __import__("core.agent_registry", fromlist=["AgentRegistry"]).AgentRegistry()
    )

    # Service Registry
    service_registry = providers.Singleton(
        lambda: __import__("core.service_registry", fromlist=["ServiceRegistry"]).ServiceRegistry()
    )

    # Intelligence Broker
    intelligence_broker = providers.Singleton(
        lambda: __import__(
            "core.intelligence_broker", fromlist=["IntelligenceBroker"]
        ).IntelligenceBroker()
    )

    # ========================================================================
    # VALIDATION LAYER
    # ========================================================================

    # Intelligence Validator
    intelligence_validator = providers.Singleton(
        lambda: __import__(
            "validation.intelligence_validator", fromlist=["IntelligenceValidator"]
        ).IntelligenceValidator()
    )

    # ========================================================================
    # CONNECTOR LAYER
    # ========================================================================

    # CoinGecko Connector
    coingecko_connector = providers.Singleton(
        lambda: __import__(
            "connectors.price_intelligence.coingecko_connector", fromlist=["CoinGeckoConnector"]
        ).CoinGeckoConnector()
    )


# Global container instance
_container: ApplicationContainer | None = None


def get_container() -> ApplicationContainer:
    """
    Get the global application container.

    Returns:
        ApplicationContainer: Singleton container instance

    Example:
        container = get_container()
        broker = container.intelligence_broker()
        postgres = container.postgres_manager()
    """
    global _container
    if _container is None:
        _container = ApplicationContainer()
        logger.info("DI Container initialized")
    return _container


def reset_container():
    """
    Reset the global container (useful for testing).

    Example:
        # In test setup
        reset_container()
        container = get_container()
        # Override providers with mocks
        container.redis_manager.override(mock_redis)
    """
    global _container
    _container = None
    logger.debug("DI Container reset")


async def initialize_container():
    """
    Initialize all singleton dependencies in the container.

    Call this on application startup to ensure all singletons
    are created and resources are initialized.

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await initialize_container()
            yield
            # Shutdown
            await shutdown_container()
    """
    container = get_container()

    logger.info("Initializing DI container dependencies...")

    # Initialize infrastructure components
    try:
        redis_manager = container.redis_manager()
        redis_manager.connect()
        logger.info("✅ Redis Manager initialized")
    except Exception as e:
        logger.warning(f"⚠️  Redis initialization failed: {e}")

    try:
        kafka_manager = container.kafka_manager()
        kafka_manager.connect()
        logger.info("✅ Kafka Manager initialized")
    except Exception as e:
        logger.warning(f"⚠️  Kafka initialization failed: {e}")

    try:
        postgres_manager = container.postgres_manager()
        await postgres_manager.connect()
        logger.info("✅ PostgreSQL Manager initialized")
    except Exception as e:
        logger.warning(f"⚠️  PostgreSQL initialization failed: {e}")

    # Initialize core components (they auto-initialize on first access)
    container.agent_registry()
    container.service_registry()
    container.intelligence_broker()
    logger.info("✅ Core components initialized")

    # Initialize memory components
    container.short_term_memory()
    container.long_term_memory()
    logger.info("✅ Memory components initialized")

    # Initialize validators
    container.intelligence_validator()
    logger.info("✅ Validators initialized")

    # Initialize connectors
    container.coingecko_connector()
    logger.info("✅ Connectors initialized")

    logger.info("🎉 DI Container fully initialized")


async def shutdown_container():
    """
    Shutdown all container dependencies and release resources.

    Call this on application shutdown to ensure proper cleanup.

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await initialize_container()
            yield
            # Shutdown
            await shutdown_container()
    """
    container = get_container()

    logger.info("Shutting down DI container...")

    # Shutdown infrastructure components
    try:
        redis_manager = container.redis_manager()
        redis_manager.disconnect()
        logger.info("Redis Manager shutdown")
    except Exception as e:
        logger.error(f"Redis shutdown error: {e}")

    try:
        kafka_manager = container.kafka_manager()
        kafka_manager.disconnect()
        logger.info("Kafka Manager shutdown")
    except Exception as e:
        logger.error(f"Kafka shutdown error: {e}")

    try:
        postgres_manager = container.postgres_manager()
        await postgres_manager.disconnect()
        logger.info("PostgreSQL Manager shutdown")
    except Exception as e:
        logger.error(f"PostgreSQL shutdown error: {e}")

    logger.info("DI Container shutdown complete")


# ============================================================================
# BACKWARD COMPATIBILITY HELPERS
# ============================================================================


def get_redis_manager():
    """Get Redis Manager from container (backward compatible)."""
    return get_container().redis_manager()


def get_kafka_manager():
    """Get Kafka Manager from container (backward compatible)."""
    return get_container().kafka_manager()


def get_postgres_manager():
    """Get PostgreSQL Manager from container (backward compatible)."""
    return get_container().postgres_manager()


def get_short_term_memory():
    """Get Short-Term Memory from container (backward compatible)."""
    return get_container().short_term_memory()


def get_long_term_memory():
    """Get Long-Term Memory from container (backward compatible)."""
    return get_container().long_term_memory()


def get_agent_registry():
    """Get Agent Registry from container (backward compatible)."""
    return get_container().agent_registry()


def get_service_registry():
    """Get Service Registry from container (backward compatible)."""
    return get_container().service_registry()


def get_intelligence_broker():
    """Get Intelligence Broker from container (backward compatible)."""
    return get_container().intelligence_broker()


def get_intelligence_validator():
    """Get Intelligence Validator from container (backward compatible)."""
    return get_container().intelligence_validator()


def get_coingecko_connector():
    """Get CoinGecko Connector from container (backward compatible)."""
    return get_container().coingecko_connector()
