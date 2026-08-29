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

from unittest.mock import patch
from app.models.document import Document
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship

@patch('app.api.documents.search_corporate_ir_documents')
def test_documents_search_reaches_collector_ae(mock_search):
    mock_doc = Document(title='mock', country_code='AE', organization='mock_org', document_type='mock')
    mock_ent = IntelligenceEntity(id='e1', type='mock', label='mock')
    mock_rel = IntelligenceRelationship(source='e1', target='e2', type='mock', confidence='high')

    mock_search.return_value = ([mock_doc], [mock_ent], [mock_rel])

    response = client.post('/api/documents/search', json={
        'query': 'report',
        'country_code': 'AE',
        'organization': 'emirates_nbd',
        'document_type': 'report'
    })

    assert response.status_code == 200
    mock_search.assert_called_once()
    req_arg = mock_search.call_args[0][0]
    assert req_arg.country_code == 'AE'
    assert req_arg.organization == 'emirates_nbd'

    data = response.json()
    assert data['status'] == 'collected'
