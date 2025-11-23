"""
Basic health check tests for CIAL
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint returns 200"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CIAL"
    assert "version" in data
    assert "components" in data


def test_root_endpoint():
    """Test root endpoint returns welcome message"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "CIAL" in data["message"]
    assert "version" in data
    assert "documentation" in data
    assert "endpoints" in data


def test_api_documentation_endpoints():
    """Test API documentation endpoints are accessible"""
    # Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200

    # ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200

    # OpenAPI schema
    response = client.get("/api/openapi.json")
    assert response.status_code == 200


@pytest.mark.unit
def test_intelligence_stream_endpoint():
    """Test intelligence stream endpoint placeholder"""
    response = client.get("/api/v1/intelligence/stream/price.critical")
    assert response.status_code == 200
    data = response.json()
    assert data["stream_type"] == "price.critical"
    assert data["status"] == "pending_implementation"


@pytest.mark.unit
def test_agent_status_endpoint():
    """Test agent status endpoint placeholder"""
    response = client.get("/api/v1/agents/test-agent-123/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "test-agent-123"
    assert data["status"] == "pending_implementation"
