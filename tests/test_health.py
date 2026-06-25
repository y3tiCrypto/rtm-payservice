import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy import text
from app.main import app
from app.database import get_db

def test_health_check_healthy(mocker):
    # Mock Database Session
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    
    # Override FastAPI DB dependency
    def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock RPC daemon connection
    mock_rpc = mocker.patch("app.rpc_client.rpc")
    mock_rpc.rpc.getblockchaininfo.return_value = {"blocks": 250000}
    
    # Force settings mock
    mocker.patch("app.config.settings.redis_enabled", False)
    
    client = TestClient(app)
    response = client.get("/api/health")
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert json_data["database"] == "healthy"
    assert json_data["rpc"] == "healthy"
    assert json_data["redis"] == "disabled"
    
    # Clean up FastAPI dependency overrides
    app.dependency_overrides.clear()

def test_health_check_unhealthy_db(mocker):
    # Mock DB failure
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB Connection Refused")
    
    def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock RPC success
    mock_rpc = mocker.patch("app.rpc_client.rpc")
    mock_rpc.rpc.getblockchaininfo.return_value = {"blocks": 250000}
    
    mocker.patch("app.config.settings.redis_enabled", False)
    
    client = TestClient(app)
    response = client.get("/api/health")
    
    assert response.status_code == 503
    json_data = response.json()["detail"]
    assert json_data["status"] == "unhealthy"
    assert json_data["database"].startswith("unhealthy:")
    assert json_data["rpc"] == "healthy"
    
    app.dependency_overrides.clear()
