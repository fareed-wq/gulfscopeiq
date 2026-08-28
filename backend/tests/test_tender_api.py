from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.tender import Tender

client = TestClient(app)

def test_tender_search_valid():
    response = client.post("/api/tenders/search", json={
        "query": "cybersecurity",
        "country_code": "SA"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "cybersecurity"
    assert data["country_code"] == "SA"
    assert data["status"] == "foundation"
    assert data["tenders"] == []
    assert data["entities"] == []
    assert data["relationships"] == []

def test_tender_search_whitespace_normalization():
    response = client.post("/api/tenders/search", json={
        "query": "  cybersecurity   services  ",
        "country_code": " sa "
    })
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "cybersecurity services"
    assert data["country_code"] == "SA"

def test_tender_search_empty_rejected():
    response = client.post("/api/tenders/search", json={
        "query": "   "
    })
    assert response.status_code == 422

def test_tender_search_mutable_defaults():
    response1 = client.post("/api/tenders/search", json={"query": "test1"})
    data1 = response1.json()
    assert data1["tenders"] == []

    response2 = client.post("/api/tenders/search", json={"query": "test2"})
    data2 = response2.json()
    assert data2["tenders"] == []

@patch("app.api.tender.search_qatar_tenders", new_callable=AsyncMock)
def test_tender_search_qatar(mock_search):
    # Mock the return value
    mock_search.return_value = ([
        Tender(title="QA Tender 1", country_code="QA")
    ], [], [])

    response = client.post("/api/tenders/search", json={
        "query": "cybersecurity",
        "country_code": "qa"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "cybersecurity"
    assert data["country_code"] == "QA"
    assert data["status"] == "collected"
    assert len(data["tenders"]) == 1
    assert data["tenders"][0]["title"] == "QA Tender 1"

@patch("app.api.tender.search_kuwait_tenders", new_callable=AsyncMock)
def test_tender_search_kuwait(mock_search):
    mock_search.return_value = ([
        Tender(title="KW Tender 1", country_code="KW", status="opening")
    ], [], [])

    response = client.post("/api/tenders/search", json={
        "query": "security",
        "country_code": "kw"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "security"
    assert data["country_code"] == "KW"
    assert data["status"] == "collected"
    assert len(data["tenders"]) == 1
    assert data["tenders"][0]["title"] == "KW Tender 1"

def test_tender_search_non_kw_qa_still_foundation():
    response = client.post("/api/tenders/search", json={
        "query": "test",
        "country_code": "AE"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "foundation"
    assert data["tenders"] == []

@patch('app.api.tender.search_bahrain_tenders', new_callable=AsyncMock)
def test_tender_search_bahrain(mock_search):
    mock_search.return_value = ([
        Tender(title='BH Tender 1', country_code='BH')
    ], [], [])

    response = client.post('/api/tenders/search', json={
        'query': 'security',
        'country_code': 'bh'
    })
    assert response.status_code == 200
    data = response.json()
    assert data['query'] == 'security'
    assert data['country_code'] == 'BH'
    assert data['status'] == 'collected'
    assert len(data['tenders']) == 1
    assert data['tenders'][0]['title'] == 'BH Tender 1'
