from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

from unittest.mock import patch, AsyncMock

def test_company_investigate_valid():
    with patch("app.api.company.discover_website", new_callable=AsyncMock) as mock_disc:
        with patch("app.api.company.discover_news", new_callable=AsyncMock) as mock_news:
            mock_disc.return_value = None
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
    with patch("app.api.company.discover_website", new_callable=AsyncMock) as mock_disc:
        with patch("app.api.company.discover_news", new_callable=AsyncMock) as mock_news:
            mock_disc.return_value = None
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
        with patch("app.api.company.discover_news", new_callable=AsyncMock) as mock_news:
            response = client.post("/api/company/investigate", json={
                "company_name": "Example Company",
                "website": "example.com"
            })
            assert response.status_code == 200
            mock_investigate.assert_called_once()

def test_company_investigate_with_provided_website():
    with patch("app.api.company.discover_website", new_callable=AsyncMock) as mock_disc:
        with patch("app.api.company.investigate_website", new_callable=AsyncMock) as mock_inv:
            with patch("app.api.company.discover_news", new_callable=AsyncMock) as mock_news:
                response = client.post("/api/company/investigate", json={
                    "company_name": "Example Company",
                    "website": "https://example.com"
                })
                assert response.status_code == 200

                # Should not call discovery since website provided
                mock_disc.assert_not_called()
                # Should investigate the provided website
                mock_inv.assert_called_once()

def test_company_investigate_with_discovered_website():
    with patch("app.api.company.discover_website", new_callable=AsyncMock) as mock_disc:
        with patch("app.api.company.investigate_website", new_callable=AsyncMock) as mock_inv:
            with patch("app.api.company.discover_news", new_callable=AsyncMock) as mock_news:
                # Mock discovery finding a website
                mock_disc.return_value = "https://discovered.com"

                response = client.post("/api/company/investigate", json={
                    "company_name": "Example Company"
                })
                assert response.status_code == 200
                mock_disc.assert_called_once()
                mock_inv.assert_called_once()

def test_company_investigate_malformed_registry():
    with patch("app.api.company.discover_website", new_callable=AsyncMock) as mock_disc:
        mock_disc.return_value = None
        response = client.post("/api/company/investigate", json={
            "company_name": "Example Company",
            "registry_data": {
                "registration_number": ["an array is not a string"]
            }
        })
        assert response.status_code == 422 # Unprocessable Entity (Pydantic validation failure)

def test_company_investigate_valid_registry():
    with patch("app.api.company.discover_website", new_callable=AsyncMock) as mock_disc:
        with patch("app.api.company.discover_news", new_callable=AsyncMock) as mock_news:
            mock_disc.return_value = None
            response = client.post("/api/company/investigate", json={
                "company_name": "Example Company",
                "country_code": "SA",
                "registration_number": " 123456 ",
                "registry_data": {
                    "legal_name": "Example LLC",
                    "city": "Riyadh"
                }
            })
            assert response.status_code == 200
            data = response.json()
            assert data["company"]["country"] == "SA"
            assert data["company"]["registration_number"] == "123456" # But note: registry_data process sets the registration_number? Actually the payload registration_number sets it.
            # Check registry data
            reg = data["company"]["attributes"]["registry"]
            assert reg["legal_name"] == "Example LLC"
            assert reg["city"] == "Riyadh"
