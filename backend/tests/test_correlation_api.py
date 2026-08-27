from fastapi.testclient import TestClient
from app.main import app
from app.intelligence.correlation import _generate_deterministic_id, normalize_organization_name

client = TestClient(app)

def test_correlation_analyze_endpoint():
    payload = {
        "entities": [
            {"id": "1", "type": "Organization", "label": "SABIC", "attributes": {}},
            {"id": "2", "type": "Organization", "label": "sabic", "attributes": {}}
        ],
        "relationships": []
    }
    
    response = client.post("/api/correlation/analyze", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "correlated"
    assert len(data["entities"]) == 1
    
    expected_id = _generate_deterministic_id(normalize_organization_name("SABIC"))
    
    assert data["entities"][0]["id"] == expected_id
    
    assert "stats" in data
    assert data["stats"]["input_entities"] == 2
    assert data["stats"]["canonical_entities"] == 1
    
    assert "organization_clusters" in data
    assert len(data["organization_clusters"]) == 1
    
    cluster = data["organization_clusters"][0]
    assert cluster["organization_id"] == expected_id
    assert cluster["organization_name"] == "SABIC"

def test_correlation_analyze_empty():
    response = client.post("/api/correlation/analyze", json={"entities": [], "relationships": []})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "correlated"
    assert len(data["entities"]) == 0
    assert len(data["organization_clusters"]) == 0
