from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

@patch('app.api.jobs.search_successfactors_jobs', new_callable=AsyncMock)
def test_jobs_search_valid(mock_search):
    mock_search.return_value = ([], [], [], 'collected')

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
    assert data["status"] == "collected"
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

from unittest.mock import patch, AsyncMock
from app.models.job import Job

@patch('app.api.jobs.search_successfactors_jobs', new_callable=AsyncMock)
def test_jobs_search_sa_successfactors(mock_search):
    mock_search.return_value = ([Job(title='SF Job 1', country_code='SA', company='STC')], [], [], 'collected')

    response = client.post('/api/jobs/search', json={
        'query': 'engineer',
        'country_code': 'SA',
        'company': 'stc'
    })

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'collected'
    assert len(data['jobs']) == 1
    assert data['jobs'][0]['title'] == 'SF Job 1'

def test_jobs_search_sa_unsupported_company():
    response = client.post('/api/jobs/search', json={
        'query': 'engineer',
        'country_code': 'SA',
        'company': 'Unknown Company'
    })

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'foundation'
    assert len(data['jobs']) == 0
