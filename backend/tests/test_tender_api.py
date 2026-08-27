from fastapi.testclient import TestClient
from app.main import app

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
