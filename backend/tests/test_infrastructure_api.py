import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

client = TestClient(app)

@patch('app.api.infrastructure.investigate_infrastructure')
def test_infrastructure_api_success(mock_inv):
    mock_inv.return_value = {
        "status": "collected",
        "profile": {
            "domain": "sabic.com",
            "status": "collected",
            "registrar": "Test",
            "ipv4": ["8.8.8.8"]
        },
        "entities": [],
        "relationships": []
    }
    
    resp = client.post("/api/infrastructure/investigate", json={"domain": "sabic.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "collected"
    assert data["profile"]["domain"] == "sabic.com"
    assert data["profile"]["ipv4"] == ["8.8.8.8"]

def test_infrastructure_api_invalid_domain():
    resp = client.post("/api/infrastructure/investigate", json={"domain": "192.168.1.1"})
    assert resp.status_code == 422
    assert "Invalid domain" in resp.text
