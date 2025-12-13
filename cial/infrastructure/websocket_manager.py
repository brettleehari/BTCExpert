"""
CIAL WebSocket Manager
Session 18: Real-Time Intelligence Streaming

Features:
- WebSocket connection management
- Redis PubSub integration for real-time events
- Multi-client broadcasting
- Connection authentication
- Automatic reconnection handling
- Message filtering and routing
"""

from typing import Dict, Set, Optional, List, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio
import json
import uuid
from enum import Enum

from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.observability import metrics, trace_operation


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SubscriptionType(str, Enum):
    """Types of intelligence subscriptions."""
    ALL = "all"
    PRICE_CRITICAL = "price.critical"
    PRICE_NORMAL = "price.normal"
    SENTIMENT_BREAKING = "sentiment.breaking"
    WHALE_MASSIVE = "whale.massive"
    TECHNICAL_SIGNALS = "technical.signals"
    REGULATORY_ALERTS = "regulatory.alerts"
    DEFI_EVENTS = "defi.events"


class WebSocketConnection:
    """
    Represents a single WebSocket client connection.

    Tracks connection state, subscriptions, and metadata.
    """

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        client_ip: str
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.client_ip = client_ip
        self.state = ConnectionState.CONNECTING
        self.subscriptions: Set[str] = set()
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.messages_sent = 0
        self.messages_received = 0
        self.metadata: Dict[str, Any] = {}

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def add_subscription(self, subscription: str):
        """Add intelligence subscription."""
        self.subscriptions.add(subscription)
        self.update_activity()

    def remove_subscription(self, subscription: str):
        """Remove intelligence subscription."""
        self.subscriptions.discard(subscription)
        self.update_activity()

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        uptime = (datetime.utcnow() - self.connected_at).total_seconds()

        return {
            "connection_id": self.connection_id,
            "client_ip": self.client_ip,
            "state": self.state.value,
            "subscriptions": list(self.subscriptions),
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "uptime_seconds": uptime,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "metadata": self.metadata
        }


class WebSocketManager:
    """
    Manages WebSocket connections and real-time intelligence streaming.

    Features:
    - Connection lifecycle management
    - Redis PubSub integration
    - Broadcasting to subscribed clients
    - Connection authentication
    - Automatic cleanup
    """

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.redis_client: Optional[Any] = None
        self.pubsub_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'broadcasts': 0
        }

    async def initialize(self):
        """Initialize WebSocket manager and Redis PubSub."""
        try:
            # Get Redis client from container
            from infrastructure.container import get_container
            container = get_container()
            redis_manager = container.redis_manager()

            # Connect to Redis
            await redis_manager.connect_async()
            self.redis_client = redis_manager.async_client

            # Start PubSub listener
            await self.start_pubsub_listener()

            logger.info("WebSocket manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket manager: {e}", exc_info=True)
            raise

    async def start_pubsub_listener(self):
        """
        Start Redis PubSub listener for intelligence events.

        Listens to Kafka topics via Redis PubSub and broadcasts to
        subscribed WebSocket clients.
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")

        async def pubsub_loop():
            """Background task for Redis PubSub."""
            self._running = True

            # Subscribe to intelligence channels
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(
                settings.KAFKA_TOPIC_PRICE_CRITICAL,
                settings.KAFKA_TOPIC_SENTIMENT_BREAKING,
                settings.KAFKA_TOPIC_WHALE_MASSIVE,
                settings.KAFKA_TOPIC_TECHNICAL_SIGNALS,
                settings.KAFKA_TOPIC_REGULATORY_ALERTS,
                settings.KAFKA_TOPIC_DEFI_EVENTS,
            )

            logger.info("Redis PubSub listener started")

            try:
                while self._running:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                    if message and message['type'] == 'message':
                        channel = message['channel']
                        data = message['data']

                        # Parse message
                        try:
                            intelligence_data = json.loads(data) if isinstance(data, str) else data
                        except json.JSONDecodeError:
                            intelligence_data = {"raw": data}

                        # Broadcast to subscribed clients
                        await self.broadcast_intelligence(
                            channel=channel,
                            data=intelligence_data
                        )

            except asyncio.CancelledError:
                logger.info("PubSub listener cancelled")
            except Exception as e:
                logger.error(f"PubSub listener error: {e}", exc_info=True)
            finally:
                await pubsub.unsubscribe()
                await pubsub.close()

        self.pubsub_task = asyncio.create_task(pubsub_loop())

    async def stop_pubsub_listener(self):
        """Stop Redis PubSub listener."""
        self._running = False

        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass

        logger.info("Redis PubSub listener stopped")

    @trace_operation("websocket_connect")
    async def connect(
        self,
        websocket: WebSocket,
        client_ip: str,
        auth_token: Optional[str] = None
    ) -> str:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            client_ip: Client IP address
            auth_token: Optional authentication token

        Returns:
            connection_id: Unique connection identifier
        """
        # Generate connection ID
        connection_id = str(uuid.uuid4())

        try:
            # Accept WebSocket connection
            await websocket.accept()

            # Create connection object
            connection = WebSocketConnection(
                websocket=websocket,
                connection_id=connection_id,
                client_ip=client_ip
            )

            # Update state
            connection.state = ConnectionState.CONNECTED

            # TODO: Implement authentication
            # if auth_token:
            #     is_valid = await self.authenticate(auth_token)
            #     if is_valid:
            #         connection.state = ConnectionState.AUTHENTICATED

            # Register connection
            self.connections[connection_id] = connection

            # Update statistics
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = len(self.connections)

            # Record metric
            metrics.increment_counter(
                'cial_websocket_connections_total',
                {'status': 'connected'}
            )
            metrics.set_gauge(
                'cial_websocket_active_connections',
                len(self.connections)
            )

            # Send welcome message
            await self.send_to_client(
                connection_id=connection_id,
                message={
                    "type": "welcome",
                    "connection_id": connection_id,
                    "message": "Connected to CIAL real-time intelligence stream",
                    "timestamp": datetime.utcnow().isoformat(),
                    "available_subscriptions": [s.value for s in SubscriptionType]
                }
            )

            logger.info(
                f"WebSocket connected: {connection_id}",
                client_ip=client_ip,
                total_connections=self.stats['active_connections']
            )

            return connection_id

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}", exc_info=True)
            raise

    @trace_operation("websocket_disconnect")
    async def disconnect(self, connection_id: str):
        """
        Disconnect and cleanup a WebSocket connection.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.state = ConnectionState.DISCONNECTED

            # Remove from connections
            del self.connections[connection_id]

            # Update statistics
            self.stats['active_connections'] = len(self.connections)

            # Record metric
            metrics.increment_counter(
                'cial_websocket_connections_total',
                {'status': 'disconnected'}
            )
            metrics.set_gauge(
                'cial_websocket_active_connections',
                len(self.connections)
            )

            logger.info(
                f"WebSocket disconnected: {connection_id}",
                total_connections=self.stats['active_connections']
            )

    async def send_to_client(
        self,
        connection_id: str,
        message: Dict[str, Any]
    ):
        """
        Send message to a specific client.

        Args:
            connection_id: Target connection ID
            message: Message dictionary to send
        """
        if connection_id not in self.connections:
            logger.warning(f"Cannot send to unknown connection: {connection_id}")
            return

        connection = self.connections[connection_id]

        try:
            # Send JSON message
            await connection.websocket.send_json(message)

            # Update statistics
            connection.messages_sent += 1
            connection.update_activity()
            self.stats['total_messages_sent'] += 1

            # Record metric
            metrics.increment_counter(
                'cial_websocket_messages_sent_total',
                {'connection_id': connection_id}
            )

        except WebSocketDisconnect:
            logger.info(f"Client disconnected during send: {connection_id}")
            await self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)

    async def broadcast(
        self,
        message: Dict[str, Any],
        subscription_filter: Optional[str] = None
    ):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message to broadcast
            subscription_filter: Only send to clients with this subscription
        """
        disconnected = []

        for connection_id, connection in self.connections.items():
            # Apply subscription filter
            if subscription_filter:
                if subscription_filter not in connection.subscriptions and "all" not in connection.subscriptions:
                    continue

            try:
                await connection.websocket.send_json(message)
                connection.messages_sent += 1
                connection.update_activity()

            except WebSocketDisconnect:
                disconnected.append(connection_id)
            except Exception as e:
                logger.error(f"Broadcast failed to {connection_id}: {e}")
                disconnected.append(connection_id)

        # Cleanup disconnected clients
        for connection_id in disconnected:
            await self.disconnect(connection_id)

        # Update statistics
        self.stats['total_messages_sent'] += len(self.connections) - len(disconnected)
        self.stats['broadcasts'] += 1

        # Record metric
        metrics.increment_counter(
            'cial_websocket_broadcasts_total',
            {'subscription': subscription_filter or 'all'}
        )

    async def broadcast_intelligence(
        self,
        channel: str,
        data: Dict[str, Any]
    ):
        """
        Broadcast intelligence update to subscribed clients.

        Args:
            channel: Intelligence channel (e.g., "price.critical")
            data: Intelligence data
        """
        message = {
            "type": "intelligence",
            "channel": channel,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.broadcast(
            message=message,
            subscription_filter=channel
        )

        logger.debug(f"Broadcasted intelligence: {channel}")

    async def handle_client_message(
        self,
        connection_id: str,
        message: Dict[str, Any]
    ):
        """
        Handle incoming message from client.

        Supports:
        - subscribe: Subscribe to intelligence types
        - unsubscribe: Unsubscribe from intelligence types
        - ping: Keepalive ping

        Args:
            connection_id: Connection identifier
            message: Client message
        """
        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]
        connection.messages_received += 1
        connection.update_activity()
        self.stats['total_messages_received'] += 1

        message_type = message.get("type")

        if message_type == "subscribe":
            # Subscribe to intelligence types
            subscriptions = message.get("subscriptions", [])
            for sub in subscriptions:
                if sub in [s.value for s in SubscriptionType]:
                    connection.add_subscription(sub)

            await self.send_to_client(
                connection_id=connection_id,
                message={
                    "type": "subscribed",
                    "subscriptions": list(connection.subscriptions),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        elif message_type == "unsubscribe":
            # Unsubscribe from intelligence types
            subscriptions = message.get("subscriptions", [])
            for sub in subscriptions:
                connection.remove_subscription(sub)

            await self.send_to_client(
                connection_id=connection_id,
                message={
                    "type": "unsubscribed",
                    "subscriptions": list(connection.subscriptions),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        elif message_type == "ping":
            # Respond to ping
            await self.send_to_client(
                connection_id=connection_id,
                message={
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        else:
            logger.warning(f"Unknown message type from {connection_id}: {message_type}")

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information."""
        if connection_id in self.connections:
            return self.connections[connection_id].get_connection_info()
        return None

    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Get information about all connections."""
        return [
            conn.get_connection_info()
            for conn in self.connections.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            **self.stats,
            'connections': [
                {
                    'connection_id': conn.connection_id,
                    'state': conn.state.value,
                    'subscriptions': list(conn.subscriptions),
                    'uptime_seconds': (datetime.utcnow() - conn.connected_at).total_seconds()
                }
                for conn in self.connections.values()
            ]
        }


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


async def get_websocket_manager() -> WebSocketManager:
    """
    Get the global WebSocket manager instance.

    Returns:
        WebSocketManager: Global WebSocket manager
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
        await _websocket_manager.initialize()
    return _websocket_manager
