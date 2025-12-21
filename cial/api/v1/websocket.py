"""
CIAL WebSocket API
Session 18: Real-Time Intelligence Streaming

WebSocket endpoints for real-time intelligence delivery.
"""

import json
from typing import Any

from api.models.responses import VersionedResponse, error_response, success_response
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from infrastructure.logging_config import logger
from infrastructure.observability import trace_operation
from infrastructure.websocket_manager import get_websocket_manager

router = APIRouter()


@router.websocket("/stream")
async def intelligence_stream(
    websocket: WebSocket,
    auth_token: str | None = Query(None, description="Optional authentication token"),
):
    """
    WebSocket endpoint for real-time intelligence streaming.

    Clients can connect to this endpoint to receive real-time intelligence
    updates as they occur. Supports filtering by intelligence type through
    subscriptions.

    **Connection Flow:**
    1. Client connects to /api/v1/websocket/stream
    2. Server sends welcome message with connection_id
    3. Client subscribes to intelligence types
    4. Server streams matching intelligence updates
    5. Client can unsubscribe/resubscribe as needed

    **Message Format (Client → Server):**
    ```json
    {
      "type": "subscribe",
      "subscriptions": ["price.critical", "sentiment.breaking"]
    }
    ```

    **Message Format (Server → Client):**
    ```json
    {
      "type": "intelligence",
      "channel": "price.critical",
      "data": {
        "symbol": "bitcoin",
        "price": 42000,
        "change_24h": 5.2
      },
      "timestamp": "2025-12-13T10:30:00Z"
    }
    ```

    **Supported Message Types:**
    - `subscribe`: Subscribe to intelligence channels
    - `unsubscribe`: Unsubscribe from channels
    - `ping`: Keepalive ping (responds with pong)

    **Available Subscriptions:**
    - `all`: All intelligence updates
    - `price.critical`: Critical price movements
    - `price.normal`: Normal price updates
    - `sentiment.breaking`: Breaking sentiment news
    - `whale.massive`: Massive whale movements
    - `technical.signals`: Technical analysis signals
    - `regulatory.alerts`: Regulatory alerts
    - `defi.events`: DeFi events

    Args:
        websocket: WebSocket connection
        auth_token: Optional authentication token (future: JWT)

    Examples:
        **JavaScript Client:**
        ```javascript
        const ws = new WebSocket('ws://localhost:8000/api/v1/websocket/stream');

        ws.onopen = () => {
          console.log('Connected to CIAL stream');

          // Subscribe to price alerts
          ws.send(JSON.stringify({
            type: 'subscribe',
            subscriptions: ['price.critical', 'whale.massive']
          }));
        };

        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          console.log('Intelligence update:', message);
        };
        ```

        **Python Client:**
        ```python
        import asyncio
        import websockets
        import json

        async def stream_intelligence():
            async with websockets.connect('ws://localhost:8000/api/v1/websocket/stream') as ws:
                # Subscribe
                await ws.send(json.dumps({
                    'type': 'subscribe',
                    'subscriptions': ['all']
                }))

                # Receive updates
                async for message in ws:
                    data = json.loads(message)
                    print(f"Intelligence: {data}")

        asyncio.run(stream_intelligence())
        ```
    """
    ws_manager = await get_websocket_manager()

    # Get client IP
    client_ip = websocket.client.host if websocket.client else "unknown"

    # Connect client
    connection_id = await ws_manager.connect(
        websocket=websocket, client_ip=client_ip, auth_token=auth_token
    )

    logger.info(f"WebSocket client connected: {connection_id} from {client_ip}")

    try:
        # Message handling loop
        while True:
            # Receive message from client
            message = await websocket.receive_text()

            try:
                # Parse JSON message
                data = json.loads(message)

                # Handle message
                await ws_manager.handle_client_message(connection_id=connection_id, message=data)

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {connection_id}: {message}")
                await ws_manager.send_to_client(
                    connection_id=connection_id,
                    message={"type": "error", "error": "Invalid JSON format", "message": message},
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
        await ws_manager.disconnect(connection_id)

    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}", exc_info=True)
        await ws_manager.disconnect(connection_id)


@router.get("/connections")
@trace_operation("websocket_connections")
async def get_connections() -> VersionedResponse[dict[str, Any]]:
    """
    Get information about all active WebSocket connections.

    Returns:
        List of active connections with metadata

    Response includes:
    - connection_id: Unique connection identifier
    - client_ip: Client IP address
    - state: Connection state
    - subscriptions: Active subscriptions
    - connected_at: Connection timestamp
    - uptime_seconds: Connection uptime
    - messages_sent/received: Message counters
    """
    try:
        ws_manager = await get_websocket_manager()
        connections = ws_manager.get_all_connections()

        return success_response(
            data={"total_connections": len(connections), "connections": connections},
            message="Active WebSocket connections retrieved",
        )

    except Exception as e:
        logger.error(f"Failed to get connections: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve connections",
            error_code="WEBSOCKET_CONNECTIONS_ERROR",
            details={"error": str(e)},
        )


@router.get("/connection/{connection_id}")
@trace_operation("websocket_connection_info")
async def get_connection_info(connection_id: str) -> VersionedResponse[dict[str, Any]]:
    """
    Get information about a specific WebSocket connection.

    Args:
        connection_id: Connection identifier

    Returns:
        Connection details and statistics
    """
    try:
        ws_manager = await get_websocket_manager()
        connection_info = ws_manager.get_connection_info(connection_id)

        if connection_info:
            return success_response(
                data=connection_info, message="Connection information retrieved"
            )
        else:
            return error_response(
                message=f"Connection not found: {connection_id}", error_code="CONNECTION_NOT_FOUND"
            )

    except Exception as e:
        logger.error(f"Failed to get connection info: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve connection info",
            error_code="WEBSOCKET_CONNECTION_INFO_ERROR",
            details={"error": str(e)},
        )


@router.get("/stats")
@trace_operation("websocket_stats")
async def get_websocket_stats() -> VersionedResponse[dict[str, Any]]:
    """
    Get WebSocket manager statistics.

    Returns detailed statistics including:
    - Total connections (all time)
    - Active connections (current)
    - Total messages sent/received
    - Broadcast count
    - Per-connection details

    Returns:
        WebSocket manager statistics
    """
    try:
        ws_manager = await get_websocket_manager()
        stats = ws_manager.get_stats()

        return success_response(data=stats, message="WebSocket statistics retrieved")

    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve WebSocket statistics",
            error_code="WEBSOCKET_STATS_ERROR",
            details={"error": str(e)},
        )


@router.post("/broadcast")
@trace_operation("websocket_broadcast")
async def broadcast_message(
    message: dict[str, Any],
    subscription_filter: str | None = Query(
        None, description="Only broadcast to clients with this subscription"
    ),
) -> VersionedResponse[dict[str, Any]]:
    """
    Broadcast a message to all connected WebSocket clients.

    Useful for testing and manual intelligence distribution.

    Args:
        message: Message to broadcast
        subscription_filter: Optional subscription filter

    Returns:
        Broadcast result

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/websocket/broadcast" \
          -H "Content-Type: application/json" \
          -d '{
            "type": "test",
            "data": {"message": "Hello, clients!"}
          }'
        ```
    """
    try:
        ws_manager = await get_websocket_manager()

        await ws_manager.broadcast(message=message, subscription_filter=subscription_filter)

        return success_response(
            data={
                "broadcasted": True,
                "active_connections": len(ws_manager.connections),
                "subscription_filter": subscription_filter,
            },
            message="Message broadcasted successfully",
        )

    except Exception as e:
        logger.error(f"Broadcast failed: {e}", exc_info=True)
        return error_response(
            message="Failed to broadcast message",
            error_code="WEBSOCKET_BROADCAST_ERROR",
            details={"error": str(e)},
        )


@router.get("/health")
async def websocket_health() -> VersionedResponse[dict[str, Any]]:
    """
    Check WebSocket system health.

    Returns:
        WebSocket health status
    """
    try:
        ws_manager = await get_websocket_manager()

        return success_response(
            data={
                "status": "healthy",
                "active_connections": len(ws_manager.connections),
                "pubsub_running": ws_manager._running,
                "redis_connected": ws_manager.redis_client is not None,
            },
            message="WebSocket system is healthy",
        )

    except Exception as e:
        logger.error(f"WebSocket health check failed: {e}", exc_info=True)
        return error_response(
            message="WebSocket health check failed",
            error_code="WEBSOCKET_HEALTH_ERROR",
            details={"error": str(e)},
        )
