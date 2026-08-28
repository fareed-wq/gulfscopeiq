from app.models.intelligence_profile import UnifiedProfileRequest

def test_company_name_normalization():
    req = UnifiedProfileRequest(company_name="  SABIC  ", country_code="SA")
    assert req.company_name == "SABIC"

def test_country_uppercase():
    req = UnifiedProfileRequest(company_name="SABIC", country_code=" sa ")
    assert req.country_code == "SA"

def test_optional_query_normalization():
    req = UnifiedProfileRequest(company_name="SABIC", country_code="SA", query="  security   report  ")
    assert req.query == "security report"

def test_whitespace_only_query():
    req = UnifiedProfileRequest(company_name="SABIC", country_code="SA", query="   ")
    assert req.query is None


import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.intelligence_profile import UnifiedProfileRequest
from app.intelligence.unified_profile import build_unified_profile
from app.models.company import CompanyInvestigateResponse, Company
from app.models.intelligence import IntelligenceEntity

@pytest.mark.anyio
@patch('app.intelligence.unified_profile.investigate_company')
@patch('app.intelligence.unified_profile.investigate_infrastructure')
@patch('app.intelligence.unified_profile.correlate_intelligence')
async def test_infrastructure_skipped_no_website(mock_corr, mock_infra, mock_comp):
    req = UnifiedProfileRequest(company_name="SABIC", country_code="SA")

    comp_res = CompanyInvestigateResponse(
        company=Company(name="SABIC", country="SA", website=None, normalized_name="SABIC"),
        query="test", entities=[IntelligenceEntity(id="org1", type="Organization", label="SABIC", attributes={})],
        relationships=[]
    )
    mock_comp.return_value = comp_res

    mock_corr.return_value = ([], [], [], {})

    res = await build_unified_profile(req)

    assert res.modules.infrastructure.status == "skipped"
    assert not mock_infra.called

@pytest.mark.anyio
@patch('app.intelligence.unified_profile.investigate_company')
@patch('app.intelligence.unified_profile.investigate_infrastructure')
@patch('app.intelligence.unified_profile.correlate_intelligence')
async def test_infrastructure_collected_with_website(mock_corr, mock_infra, mock_comp):
    req = UnifiedProfileRequest(company_name="SABIC", country_code="SA")

    comp_res = CompanyInvestigateResponse(
        company=Company(name="SABIC", country="SA", website="https://www.sabic.com/en", normalized_name="SABIC"),
        query="test", entities=[IntelligenceEntity(id="org1", type="Organization", label="SABIC", attributes={})],
        relationships=[]
    )
    mock_comp.return_value = comp_res

    mock_infra.return_value = {
        "status": "collected",
        "profile": MagicMock(),
        "entities": [
            IntelligenceEntity(id="dom1", type="Domain", label="www.sabic.com", attributes={}),
            IntelligenceEntity(id="ip1", type="IPAddress", label="8.8.8.8", attributes={})
        ],
        "relationships": []
    }

    def corr_side_effect(entities, rels):
        # ensure relationships have operates edge
        has_operates = any(r.type == "operates" and r.source == "org1" and r.target == "dom1" for r in rels)
        assert has_operates
        return (entities, rels, [], {})

    mock_corr.side_effect = corr_side_effect

    res = await build_unified_profile(req)

    assert res.modules.infrastructure.status == "collected"
    assert res.modules.infrastructure.count == 2
    mock_infra.assert_called_once_with("www.sabic.com")

@pytest.mark.anyio
@patch('app.intelligence.unified_profile.investigate_company')
@patch('app.intelligence.unified_profile.investigate_infrastructure')
@patch('app.intelligence.unified_profile.correlate_intelligence')
async def test_infrastructure_partial_top_level_completed(mock_corr, mock_infra, mock_comp):
    req = UnifiedProfileRequest(company_name="SABIC", country_code="SA")

    comp_res = CompanyInvestigateResponse(
        company=Company(name="SABIC", country="SA", website="https://www.sabic.com", normalized_name="SABIC"),
        query="test", entities=[IntelligenceEntity(id="org1", type="Organization", label="SABIC", attributes={})],
        relationships=[]
    )
    mock_comp.return_value = comp_res

    mock_infra.return_value = {
        "status": "partial",
        "profile": MagicMock(),
        "entities": [],
        "relationships": []
    }
    mock_corr.return_value = ([], [], [], {})

    res = await build_unified_profile(req)

    # partial infra doesn't make top-level partial
    assert res.modules.infrastructure.status == "partial"
    assert res.status == "completed"

@pytest.mark.anyio
@patch('app.intelligence.unified_profile.investigate_company')
@patch('app.intelligence.unified_profile.investigate_infrastructure')
@patch('app.intelligence.unified_profile.correlate_intelligence')
async def test_infrastructure_error_top_level_partial(mock_corr, mock_infra, mock_comp):
    req = UnifiedProfileRequest(company_name="SABIC", country_code="SA")

    comp_res = CompanyInvestigateResponse(
        company=Company(name="SABIC", country="SA", website="https://www.sabic.com", normalized_name="SABIC"),
        query="test", entities=[IntelligenceEntity(id="org1", type="Organization", label="SABIC", attributes={})],
        relationships=[]
    )
    mock_comp.return_value = comp_res

    mock_infra.side_effect = Exception("Crash")
    mock_corr.return_value = ([], [], [], {})

    res = await build_unified_profile(req)

    assert res.modules.infrastructure.status == "error"
    assert res.status == "partial"
