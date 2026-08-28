import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.company import CompanyInvestigateResponse, Company
from app.models.job import JobSearchResponse, Job
from app.models.document import DocumentSearchResponse, Document
from app.models.tender import TenderSearchResponse, Tender
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship

client = TestClient(app)

@pytest.fixture
def mock_modules():
    with patch("app.intelligence.unified_profile.investigate_company", new_callable=AsyncMock) as m_company:
        with patch("app.intelligence.unified_profile.search_jobs", new_callable=AsyncMock) as m_jobs:
            with patch("app.intelligence.unified_profile.search_documents", new_callable=AsyncMock) as m_docs:
                with patch("app.intelligence.unified_profile.search_tenders", new_callable=AsyncMock) as m_tenders:
                    # Setup default successful mocks
                    m_company.return_value = CompanyInvestigateResponse(
                        query="SABIC",
                        query_type="company",
                        company=Company(name="SABIC", normalized_name="sabic", country="SA"),
                        entities=[
                            IntelligenceEntity(id="sabic", type="Organization", label="SABIC"),
                            IntelligenceEntity(id="news_1", type="news_article", label="News 1")
                        ],
                        relationships=[
                            IntelligenceRelationship(source="sabic", target="news_1", type="mentioned_in", confidence="high")
                        ]
                    )
                    
                    m_jobs.return_value = JobSearchResponse(
                        query="security", country_code="SA", company="SABIC", status="collected",
                        jobs=[Job(title="Sec Engineer")],
                        entities=[IntelligenceEntity(id="sabic", type="organization", label="SABIC")],
                        relationships=[]
                    )
                    
                    m_docs.return_value = DocumentSearchResponse(
                        query="security", country_code="SA", status="collected",
                        documents=[Document(title="Security Report")],
                        entities=[IntelligenceEntity(id="sabic", type="organization", label="SABIC")],
                        relationships=[]
                    )
                    
                    m_tenders.return_value = TenderSearchResponse(
                        query="security", country_code="SA", status="foundation",
                        tenders=[], entities=[], relationships=[]
                    )
                    
                    yield m_company, m_jobs, m_docs, m_tenders

def test_valid_profile_request_with_query(mock_modules):
    m_comp, m_jobs, m_docs, m_tend = mock_modules
    
    response = client.post("/api/intelligence/profile", json={
        "company_name": "SABIC",
        "country_code": "SA",
        "query": "security"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # 20. response serialization
    assert data["status"] == "completed"
    assert data["company_name"] == "SABIC"
    assert data["query"] == "security"
    
    # 6. Company result preserved
    assert data["company"]["name"] == "SABIC"
    
    # 9, 10, 11. Jobs, Documents, Tenders included when query supplied
    assert len(data["jobs"]) == 1
    assert len(data["documents"]) == 1
    assert len(data["tenders"]) == 0
    
    # 8, 17. News included and counted correctly (no duplicates)
    assert data["modules"]["news"]["status"] == "collected"
    assert data["modules"]["news"]["count"] == 1
    
    # 13, 14. correlation called, canonical Organization cluster returned
    assert len(data["organization_clusters"]) == 1
    cluster = data["organization_clusters"][0]
    assert cluster["organization_name"] == "SABIC" # based on our mock data norm
    assert "news_article" in cluster["entity_type_counts"]
    
    m_comp.assert_called_once()
    m_jobs.assert_called_once()
    m_docs.assert_called_once()
    m_tend.assert_called_once()

def test_query_null_skips_modules(mock_modules):
    m_comp, m_jobs, m_docs, m_tend = mock_modules
    
    response = client.post("/api/intelligence/profile", json={
        "company_name": "SABIC",
        "country_code": "SA"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "completed"
    
    # 12. query=null skips query-required modules
    assert data["modules"]["jobs"]["status"] == "skipped"
    assert data["modules"]["documents"]["status"] == "skipped"
    assert data["modules"]["tenders"]["status"] == "skipped"
    
    m_comp.assert_called_once()
    m_jobs.assert_not_called()
    m_docs.assert_not_called()
    m_tend.assert_not_called()

def test_module_error_yields_partial(mock_modules):
    m_comp, m_jobs, m_docs, m_tend = mock_modules
    
    # Force jobs to fail
    m_jobs.side_effect = Exception("API down")
    
    response = client.post("/api/intelligence/profile", json={
        "company_name": "SABIC",
        "country_code": "SA",
        "query": "security"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # 15. one module error -> partial
    assert data["status"] == "partial"
    
    # Error isolated
    assert data["modules"]["jobs"]["status"] == "error"
    assert "failed" in data["modules"]["jobs"]["error"].lower()
    
    # 16. successful modules preserved after another fails
    assert data["modules"]["company"]["status"] == "collected"
    assert data["modules"]["documents"]["status"] == "collected"
    assert len(data["documents"]) == 1
    
    # 18. empty module results handled (tenders had 0 results)
    # 19. unsupported/foundation module state preserved
    assert data["modules"]["tenders"]["status"] == "foundation"

def test_company_failure(mock_modules):
    m_comp, m_jobs, m_docs, m_tend = mock_modules
    m_comp.side_effect = Exception("Company service down")
    
    response = client.post("/api/intelligence/profile", json={
        "company_name": "SABIC",
        "country_code": "SA"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partial"
    assert data["modules"]["company"]["status"] == "error"
    assert data["modules"]["news"]["status"] == "error" # Dependent module marks as skipped/error
    assert data["company"] is None
