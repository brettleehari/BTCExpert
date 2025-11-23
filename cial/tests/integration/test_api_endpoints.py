"""
Integration tests for API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.integration
def test_register_agent():
    """Test agent registration via API"""
    agent_data = {
        "agent_id": "integration_test_agent",
        "agent_type": "trading",
        "capabilities": {
            "intelligence_types": ["price", "sentiment"],
            "symbols": ["BTC", "ETH"],
            "min_importance": "normal",
            "real_time": True
        },
        "metadata": {"test": "integration"}
    }

    response = client.post("/api/v1/agents/register", json=agent_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["agent_id"] == "integration_test_agent"
    assert "websocket_url" in data
    assert "kafka_topics" in data
    assert len(data["kafka_topics"]) == 2


@pytest.mark.integration
def test_get_agent_status():
    """Test getting agent status via API"""
    # First register an agent
    agent_data = {
        "agent_id": "status_test_agent",
        "agent_type": "risk",
        "capabilities": {
            "intelligence_types": ["price"],
            "min_importance": "normal"
        }
    }
    client.post("/api/v1/agents/register", json=agent_data)

    # Now get its status
    response = client.get("/api/v1/agents/status_test_agent/status")
    assert response.status_code == 200

    data = response.json()
    assert data["agent_id"] == "status_test_agent"
    assert data["agent_type"] == "risk"
    assert data["status"] == "active"


@pytest.mark.integration
def test_list_agents():
    """Test listing agents via API"""
    response = client.get("/api/v1/agents/")
    assert response.status_code == 200

    data = response.json()
    assert "total" in data
    assert "agents" in data
    assert isinstance(data["agents"], list)


@pytest.mark.integration
def test_agent_stats():
    """Test getting agent statistics via API"""
    response = client.get("/api/v1/agents/stats")
    assert response.status_code == 200

    data = response.json()
    assert "total_agents" in data
    assert "active_agents" in data


@pytest.mark.integration
def test_ingest_intelligence():
    """Test ingesting intelligence via API"""
    intel_data = {
        "intelligence_type": "price",
        "source": "test_source",
        "data": {
            "current_price": 62500.0,
            "price_change_percentage_24h": 3.5
        },
        "symbol": "BTC"
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "price"
    assert data["source"] == "test_source"
    assert data["symbol"] == "BTC"
    assert "id" in data


@pytest.mark.integration
def test_get_intelligence_stream():
    """Test getting intelligence stream via API"""
    # First ingest some intelligence
    for i in range(3):
        client.post("/api/v1/intelligence/ingest", json={
            "intelligence_type": "price",
            "source": "test",
            "data": {"price": 60000 + i * 100},
            "symbol": "BTC"
        })

    # Now get the stream
    response = client.get("/api/v1/intelligence/stream/price")
    assert response.status_code == 200

    data = response.json()
    assert data["stream_type"] == "price"
    assert "messages" in data
    assert data["total"] >= 3


@pytest.mark.integration
def test_list_connectors():
    """Test listing data connectors via API"""
    response = client.get("/api/v1/intelligence/connectors")
    assert response.status_code == 200

    data = response.json()
    assert "total" in data
    assert "connectors" in data
    # Default connectors should be initialized
    assert data["total"] >= 3  # coingecko, newsapi, etherscan


@pytest.mark.integration
def test_intelligence_stats():
    """Test getting intelligence broker statistics"""
    response = client.get("/api/v1/intelligence/stats")
    assert response.status_code == 200

    data = response.json()
    assert "total_messages_processed" in data
    assert "registered_connectors" in data


@pytest.mark.integration
def test_invalid_stream_type():
    """Test requesting invalid intelligence stream type"""
    response = client.get("/api/v1/intelligence/stream/invalid_type")
    assert response.status_code == 400
    assert "Invalid stream type" in response.json()["detail"]


@pytest.mark.integration
def test_unregister_agent():
    """Test unregistering agent via API"""
    # First register
    client.post("/api/v1/agents/register", json={
        "agent_id": "delete_test_agent",
        "agent_type": "market",
        "capabilities": {"intelligence_types": ["price"]}
    })

    # Then unregister
    response = client.delete("/api/v1/agents/delete_test_agent")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

    # Verify agent is gone
    response = client.get("/api/v1/agents/delete_test_agent/status")
    assert response.status_code == 404
