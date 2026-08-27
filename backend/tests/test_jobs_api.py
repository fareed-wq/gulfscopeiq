from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_jobs_search_valid():
    response = client.post("/api/jobs/search", json={
        "query": "cybersecurity",
        "country_code": "SA",
        "company": "Aramco"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "cybersecurity"
    assert data["country_code"] == "SA"
    assert data["company"] == "Aramco"
    assert data["status"] == "foundation"
    assert data["jobs"] == []
    assert data["entities"] == []
    assert data["relationships"] == []

def test_jobs_search_whitespace_normalization():
    response = client.post("/api/jobs/search", json={
        "query": "  cybersecurity   engineer  ",
        "country_code": " bh ",
        "company": "   Saudi   Aramco  "
    })
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "cybersecurity engineer"
    assert data["country_code"] == "BH"
    assert data["company"] == "Saudi Aramco"

def test_jobs_search_country_code_uppercase():
    response = client.post("/api/jobs/search", json={
        "query": "developer",
        "country_code": "qa"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["country_code"] == "QA"

def test_jobs_search_optional_company():
    response = client.post("/api/jobs/search", json={
        "query": "engineer",
        "country_code": "KW"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["company"] is None

def test_jobs_search_company_whitespace_becomes_none():
    response = client.post("/api/jobs/search", json={
        "query": "engineer",
        "company": "   "
    })
    assert response.status_code == 200
    data = response.json()
    assert data["company"] is None

def test_jobs_search_empty_query_rejected():
    response = client.post("/api/jobs/search", json={
        "query": "   ",
        "country_code": "SA"
    })
    assert response.status_code == 422
    
def test_jobs_search_missing_query_rejected():
    response = client.post("/api/jobs/search", json={
        "country_code": "SA"
    })
    assert response.status_code == 422
