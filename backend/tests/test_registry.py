from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_gcc_registry():
    response = client.get("/api/registry/gcc")
    assert response.status_code == 200
    data = response.json()

    # all six GCC countries returned
    assert len(data) == 6
    assert set(data.keys()) == {"SA", "AE", "QA", "KW", "BH", "OM"}
    
    # country codes unique
    assert data["SA"]["country_code"] == "SA"
    
    # SA/OM tender foundation states preserved
    assert data["SA"]["tenders"] == "foundation"
    assert data["OM"]["tenders"] == "foundation"
    
    # AE tender unavailable state preserved
    assert data["AE"]["tenders"] == "unavailable"
    
    # QA/KW/BH tenders configured
    assert data["QA"]["tenders"] == "configured"
    assert data["KW"]["tenders"] == "configured"
    assert data["BH"]["tenders"] == "configured"
    
    sa_orgs = data["SA"]["organizations"]
    
    # helper
    def get_org(org_id: str):
        return next(o for o in sa_orgs if o["organization_id"] == org_id)
        
    sabic = get_org("sabic")
    saudi_aramco = get_org("saudi_aramco")
    stc = get_org("stc")
    
    # SABIC documents configured, jobs configured
    assert sabic["capabilities"]["documents"] == "configured"
    assert sabic["capabilities"]["jobs"] == "configured"
    
    # Saudi Aramco jobs configured
    assert saudi_aramco["capabilities"]["jobs"] == "configured"
    assert saudi_aramco["capabilities"]["documents"] == "foundation" # unsupported capabilities not falsely configured
    
    # STC jobs configured
    assert stc["capabilities"]["jobs"] == "configured"
    assert stc["capabilities"]["documents"] == "foundation" # unsupported capabilities not falsely configured
    
    # AE orgs check
    assert len(data["AE"]["organizations"]) == 1
    enbd = data["AE"]["organizations"][0]
    assert enbd["organization_id"] == "emirates_nbd"
    assert enbd["capabilities"]["documents"] == "configured"
    assert enbd["capabilities"]["jobs"] == "foundation"
    
    # no collector URLs exposed
    assert "https" not in response.text
