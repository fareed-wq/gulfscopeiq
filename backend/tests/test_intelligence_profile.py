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
