from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_documents_search_valid_full():
    response = client.post('/api/documents/search', json={
        'query': 'cybersecurity',
        'country_code': 'sa',
        'organization': 'Saudi Aramco',
        'document_type': 'report'
    })
    assert response.status_code == 200
    data = response.json()
    assert data['query'] == 'cybersecurity'
    assert data['country_code'] == 'SA'
    assert data['organization'] == 'Saudi Aramco'
    assert data['document_type'] == 'report'
    assert data['status'] == 'foundation'
    assert data['documents'] == []
    assert data['entities'] == []
    assert data['relationships'] == []

def test_documents_search_normalization():
    response = client.post('/api/documents/search', json={
        'query': '  cyber   security  ',
        'country_code': ' sa ',
        'organization': '  Saudi   Aramco  ',
        'document_type': '  report  '
    })
    assert response.status_code == 200
    data = response.json()
    assert data['query'] == 'cyber security'
    assert data['country_code'] == 'SA'
    assert data['organization'] == 'Saudi Aramco'
    assert data['document_type'] == 'report'

def test_documents_search_optional_missing():
    response = client.post('/api/documents/search', json={
        'query': 'cybersecurity',
        'country_code': 'SA'
    })
    assert response.status_code == 200
    data = response.json()
    assert data['organization'] is None
    assert data['document_type'] is None

def test_documents_search_optional_whitespace_only():
    response = client.post('/api/documents/search', json={
        'query': 'cybersecurity',
        'country_code': 'SA',
        'organization': '   ',
        'document_type': '   \n  '
    })
    assert response.status_code == 200
    data = response.json()
    assert data['organization'] is None
    assert data['document_type'] is None

def test_documents_search_invalid_query():
    # Empty/whitespace query
    response = client.post('/api/documents/search', json={
        'query': '   ',
        'country_code': 'SA'
    })
    assert response.status_code == 422

    # Missing query
    response2 = client.post('/api/documents/search', json={
        'country_code': 'SA'
    })
    assert response2.status_code == 422
