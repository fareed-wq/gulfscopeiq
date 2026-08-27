from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_company_investigate_valid():
    response = client.post("/api/company/investigate", json={"company_name": "Example Company"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Example Company"
    assert data["query_type"] == "company"
    assert data["status"] == "foundation"
    assert data["company"]["name"] == "Example Company"
    assert data["company"]["normalized_name"] == "example company"
    assert data["entities"] == []
    assert data["relationships"] == []

def test_company_investigate_whitespace_normalized():
    response = client.post("/api/company/investigate", json={"company_name": "   Gulf   Scope   IQ   "})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Gulf Scope IQ"
    assert data["company"]["name"] == "Gulf Scope IQ"
    assert data["company"]["normalized_name"] == "gulf scope iq"

def test_company_investigate_empty_rejected():
    response = client.post("/api/company/investigate", json={"company_name": "   "})
    assert response.status_code == 422
    
    response2 = client.post("/api/company/investigate", json={"company_name": ""})
    assert response2.status_code == 422

from unittest.mock import patch, AsyncMock
def test_company_investigate_with_website():
    with patch("app.api.company.investigate_website", new_callable=AsyncMock) as mock_investigate:
        response = client.post("/api/company/investigate", json={
            "company_name": "Example Company",
            "website": "example.com"
        })
        assert response.status_code == 200
        mock_investigate.assert_called_once()
