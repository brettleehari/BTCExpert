"""
Integration tests for STM API endpoints
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.integration
def test_store_and_get_agent_context():
    """Test storing and retrieving agent context"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.setex = Mock(return_value=True)
        mock_client.get = Mock(return_value='{"strategy": "momentum", "confidence": 0.85}')

        # Store context
        context_data = {"context": {"strategy": "momentum", "confidence": 0.85}, "ttl": 3600}

        response = client.post("/api/v1/memory/stm/test_agent/context", json=context_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent_id"] == "test_agent"

        # Get context
        response = client.get("/api/v1/memory/stm/test_agent/context")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test_agent"
        assert "context" in data


@pytest.mark.integration
def test_store_agent_decision():
    """Test storing agent decision"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.setex = Mock(return_value=True)
        mock_client.zadd = Mock(return_value=1)
        mock_client.expire = Mock(return_value=True)

        decision_data = {
            "decision": {
                "id": "decision_001",
                "action": "buy",
                "asset": "BTC",
                "amount": 0.1,
                "reasoning": "Strong bullish signal",
            },
            "ttl": 86400,
        }

        response = client.post("/api/v1/memory/stm/test_agent/decision", json=decision_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent_id"] == "test_agent"


@pytest.mark.integration
def test_get_agent_decisions():
    """Test retrieving agent decisions"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.zrevrange = Mock(return_value=["decision_001"])
        mock_client.get = Mock(return_value='{"id": "decision_001", "action": "buy"}')

        response = client.get("/api/v1/memory/stm/test_agent/decisions?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test_agent"
        assert "decisions" in data
        assert "count" in data


@pytest.mark.integration
def test_get_cached_price():
    """Test getting cached price"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.zrevrange = Mock(return_value=["price_msg_001"])

        from datetime import datetime

        from api.models.intelligence import (
            IntelligenceImportance,
            IntelligenceMessage,
            IntelligenceType,
        )

        message = IntelligenceMessage(
            id="price_msg_001",
            type=IntelligenceType.PRICE,
            importance=IntelligenceImportance.NORMAL,
            source="test",
            symbol="BTC",
            data={"current_price": 62500.0, "volume_24h": 28000000000},
            timestamp=datetime.utcnow(),
        )

        mock_client.get = Mock(return_value=message.model_dump_json())

        response = client.get("/api/v1/memory/stm/price/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC"
        assert "price_data" in data
        assert data["price_data"]["current_price"] == 62500.0


@pytest.mark.integration
def test_get_market_state():
    """Test getting market state"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.get = Mock(return_value='{"trend": "bullish", "volatility": "medium"}')

        response = client.get("/api/v1/memory/stm/test_agent/market-state")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test_agent"
        assert "market_state" in data
        assert data["market_state"]["trend"] == "bullish"


@pytest.mark.integration
def test_clear_agent_memory():
    """Test clearing agent memory"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.delete = Mock(return_value=2)

        response = client.delete("/api/v1/memory/stm/test_agent")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent_id"] == "test_agent"


@pytest.mark.integration
def test_get_stm_stats():
    """Test getting STM statistics"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.scan_iter = Mock(
            return_value=[
                "cial:stm:intelligence:price:BTC:msg1",
                "cial:stm:agent_context:agent1",
                "cial:stm:agent_decision:agent1:dec1",
            ]
        )
        mock_redis.return_value.get_info = Mock(
            return_value={"connected": True, "used_memory": "1MB"}
        )

        response = client.get("/api/v1/memory/stm/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_keys" in data


@pytest.mark.integration
def test_get_context_not_found():
    """Test getting context for non-existent agent"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.get = Mock(return_value=None)

        response = client.get("/api/v1/memory/stm/nonexistent_agent/context")
        assert response.status_code == 404
        assert "No context found" in response.json()["detail"]


@pytest.mark.integration
def test_get_price_not_cached():
    """Test getting uncached price"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value.client = mock_client
        mock_client.zrevrange = Mock(return_value=[])

        response = client.get("/api/v1/memory/stm/price/ETH")
        assert response.status_code == 404
        assert "No cached price data" in response.json()["detail"]
