"""
CIAL Kafka Manager
Event streaming for real-time intelligence distribution to agents
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError

from api.models.intelligence import IntelligenceImportance, IntelligenceMessage, IntelligenceType
from infrastructure.config import settings
from infrastructure.logging_config import logger


class KafkaManager:
    """
    Kafka manager for CIAL event streaming.

    Responsibilities:
    - Produce intelligence messages to topics
    - Topic creation and management
    - Message serialization
    - Error handling and retry logic
    """

    def __init__(self):
        self._producer: KafkaProducer | None = None
        self._admin_client: KafkaAdminClient | None = None
        self._connected = False

    def connect(self):
        """Initialize Kafka producer and admin client."""
        try:
            # Create producer with JSON serialization
            self._producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                compression_type="gzip",
            )

            # Create admin client for topic management
            self._admin_client = KafkaAdminClient(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS, client_id="cial-admin"
            )

            self._connected = True

            logger.info(
                "Kafka connected successfully", bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
            )

            # Create default topics
            self._create_default_topics()

        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}", exc_info=True)
            raise

    def disconnect(self):
        """Close Kafka connections."""
        if self._producer:
            self._producer.flush()
            self._producer.close()
            self._connected = False
            logger.info("Kafka producer closed")

        if self._admin_client:
            self._admin_client.close()
            logger.info("Kafka admin client closed")

    def _create_default_topics(self):
        """Create default intelligence topics if they don't exist."""
        default_topics = [
            # Importance-based topics
            NewTopic(name="intelligence.critical", num_partitions=3, replication_factor=1),
            NewTopic(name="intelligence.normal", num_partitions=3, replication_factor=1),
            NewTopic(name="intelligence.low", num_partitions=2, replication_factor=1),
            # Type-specific topics
            NewTopic(name="price.critical", num_partitions=2, replication_factor=1),
            NewTopic(name="price.normal", num_partitions=2, replication_factor=1),
            NewTopic(name="sentiment.breaking", num_partitions=2, replication_factor=1),
            NewTopic(name="whale.massive", num_partitions=2, replication_factor=1),
            NewTopic(name="technical.signals", num_partitions=2, replication_factor=1),
            NewTopic(name="regulatory.alerts", num_partitions=2, replication_factor=1),
            NewTopic(name="defi.events", num_partitions=2, replication_factor=1),
        ]

        try:
            self._admin_client.create_topics(new_topics=default_topics, validate_only=False)
            logger.info(f"Created {len(default_topics)} default Kafka topics")
        except TopicAlreadyExistsError:
            logger.debug("Default topics already exist")
        except Exception as e:
            logger.warning(f"Failed to create some topics: {e}")

    def publish_intelligence(
        self, message: IntelligenceMessage, topics: list[str] | None = None
    ) -> bool:
        """
        Publish intelligence message to Kafka topics.

        Args:
            message: Intelligence message to publish
            topics: List of topic names (auto-generates if None)

        Returns:
            bool: True if published successfully
        """
        if not self._connected or not self._producer:
            logger.error("Kafka producer not connected")
            return False

        try:
            # Auto-generate topics if not provided
            if topics is None:
                topics = self._get_topics_for_message(message)

            # Serialize message
            message_dict = message.model_dump()
            message_dict["timestamp"] = message.timestamp.isoformat()

            # Use message ID as key for partitioning
            key = message.id

            # Publish to all topics
            for topic in topics:
                future = self._producer.send(topic=topic, key=key, value=message_dict)

                # Add callback for error handling
                future.add_callback(self._on_send_success, topic, message.id)
                future.add_errback(self._on_send_error, topic, message.id)

            # Flush to ensure messages are sent
            self._producer.flush(timeout=5)

            logger.debug(
                "Intelligence published to Kafka",
                message_id=message.id,
                topics=topics,
                type=message.type.value,
                importance=message.importance.value,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to publish intelligence: {e}", exc_info=True)
            return False

    def _get_topics_for_message(self, message: IntelligenceMessage) -> list[str]:
        """
        Determine topics for a message based on type and importance.

        Strategy:
        - All messages go to importance-based topic (critical/normal/low)
        - CRITICAL messages also go to type-specific critical topic
        """
        topics = []

        # Importance-based topic
        importance_topic = f"intelligence.{message.importance.value.lower()}"
        topics.append(importance_topic)

        # Type-specific topic for critical messages
        if message.importance == IntelligenceImportance.CRITICAL:
            type_topic_map = {
                IntelligenceType.PRICE: "price.critical",
                IntelligenceType.SENTIMENT: "sentiment.breaking",
                IntelligenceType.WHALE: "whale.massive",
                IntelligenceType.TECHNICAL: "technical.signals",
                IntelligenceType.REGULATORY: "regulatory.alerts",
                IntelligenceType.DEFI: "defi.events",
            }

            if message.type in type_topic_map:
                topics.append(type_topic_map[message.type])

        return topics

    def _on_send_success(self, record_metadata, topic: str, message_id: str):
        """Callback for successful message send."""
        logger.debug(
            "Message sent successfully",
            topic=topic,
            partition=record_metadata.partition,
            offset=record_metadata.offset,
            message_id=message_id,
        )

    def _on_send_error(self, excp, topic: str, message_id: str):
        """Callback for failed message send."""
        logger.error("Failed to send message", topic=topic, message_id=message_id, error=str(excp))

    def create_topic(
        self, topic_name: str, num_partitions: int = 2, replication_factor: int = 1
    ) -> bool:
        """
        Create a new Kafka topic.

        Args:
            topic_name: Name of the topic
            num_partitions: Number of partitions
            replication_factor: Replication factor

        Returns:
            bool: True if created successfully
        """
        try:
            new_topic = NewTopic(
                name=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
            )

            self._admin_client.create_topics([new_topic], validate_only=False)
            logger.info(f"Created Kafka topic: {topic_name}")
            return True

        except TopicAlreadyExistsError:
            logger.debug(f"Topic already exists: {topic_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create topic {topic_name}: {e}", exc_info=True)
            return False

    def get_topics(self) -> list[str]:
        """
        Get list of all Kafka topics.

        Returns:
            List[str]: Topic names
        """
        try:
            topics = self._admin_client.list_topics()
            return list(topics)
        except Exception as e:
            logger.error(f"Failed to list topics: {e}", exc_info=True)
            return []

    def create_consumer(
        self, topics: list[str], group_id: str, auto_offset_reset: str = "latest"
    ) -> KafkaConsumer | None:
        """
        Create a Kafka consumer for specified topics.

        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading ('earliest' or 'latest')

        Returns:
            Optional[KafkaConsumer]: Consumer instance or None
        """
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                enable_auto_commit=True,
                max_poll_records=100,
            )

            logger.info("Kafka consumer created", topics=topics, group_id=group_id)

            return consumer

        except Exception as e:
            logger.error(f"Failed to create consumer: {e}", exc_info=True)
            return None

    def is_connected(self) -> bool:
        """Check if Kafka is connected."""
        return self._connected

    def get_info(self) -> dict[str, Any]:
        """Get Kafka connection information."""
        if not self.is_connected():
            return {"connected": False}

        try:
            topics = self.get_topics()
            return {
                "connected": True,
                "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "total_topics": len(topics),
                "topics": topics,
            }
        except Exception as e:
            logger.error(f"Failed to get Kafka info: {e}")
            return {"connected": True, "error": str(e)}


# Global Kafka manager instance
_kafka_manager: KafkaManager | None = None


def get_kafka_manager() -> KafkaManager:
    """
    Get the global Kafka manager instance.
    Uses singleton pattern.

    Returns:
        KafkaManager: Global Kafka manager
    """
    global _kafka_manager
    if _kafka_manager is None:
        _kafka_manager = KafkaManager()
    return _kafka_manager
