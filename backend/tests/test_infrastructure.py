import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.infrastructure import InfrastructureInvestigateRequest
from app.intelligence.infrastructure import investigate_infrastructure
import dns.resolver

def test_domain_validation():
    req = InfrastructureInvestigateRequest(domain="sabic.com")
    assert req.domain == "sabic.com"
    req = InfrastructureInvestigateRequest(domain="HTTPS://SABIC.COM/path")
    assert req.domain == "sabic.com"
    with pytest.raises(ValueError, match="Private|Invalid domain"):
        InfrastructureInvestigateRequest(domain="1.1.1.1")
    with pytest.raises(ValueError, match="Private|Invalid domain"):
        InfrastructureInvestigateRequest(domain="localhost")
    with pytest.raises(ValueError, match="Private|Invalid domain"):
        InfrastructureInvestigateRequest(domain="mycompany.internal")


# 1. NoAnswer for AAAA + otherwise successful collection => collected
@pytest.mark.anyio
@patch('dns.resolver.Resolver.resolve')
@patch('app.intelligence.infrastructure.get_domain_rdap')
@patch('app.intelligence.infrastructure.get_ip_rdap')
@patch('app.intelligence.infrastructure.get_tls_summary')
@patch('app.intelligence.infrastructure.fetch_website_safely')
async def test_investigate_infrastructure_no_aaaa_otherwise_success(mock_fetch, mock_tls, mock_ip_rdap, mock_dom_rdap, mock_resolve):
    def dns_side_effect(domain, rtype):
        if rtype == "A":
            m = MagicMock()
            m.to_text.return_value = "8.8.8.8"
            return [m]
        elif rtype == "AAAA":
            raise dns.resolver.NoAnswer()
        else:
            return []
    mock_resolve.side_effect = dns_side_effect

    mock_dom_rdap.return_value = ({"registrar": "Test"}, False)
    mock_ip_rdap.return_value = ({"network_organization": "TestOrg"}, False)
    mock_tls.return_value = (MagicMock(), False)
    mock_fetch.return_value = {"html": "<html></html>", "headers": {}}
    
    res = await investigate_infrastructure("sabic.com")
    assert res["status"] == "collected"
    assert len(res["entities"]) >= 2
    assert len(res["relationships"]) >= 1


# 2. NoNameservers + Technology/RDAP success => partial
@pytest.mark.anyio
@patch('dns.resolver.Resolver.resolve')
@patch('app.intelligence.infrastructure.get_domain_rdap')
@patch('app.intelligence.infrastructure.get_ip_rdap')
@patch('app.intelligence.infrastructure.get_tls_summary')
@patch('app.intelligence.infrastructure.fetch_website_safely')
async def test_investigate_infrastructure_nonameservers_partial(mock_fetch, mock_tls, mock_ip_rdap, mock_dom_rdap, mock_resolve):
    mock_resolve.side_effect = dns.resolver.NoNameservers()

    mock_dom_rdap.return_value = ({"registrar": "Test"}, False)
    mock_ip_rdap.return_value = ({}, False)
    mock_tls.return_value = (None, False)
    mock_fetch.return_value = {"html": "<html></html>", "headers": {}}
    
    res = await investigate_infrastructure("sabic.com")
    assert res["status"] == "partial"


# 3. LifetimeTimeout + useful surviving data => partial
@pytest.mark.anyio
@patch('dns.resolver.Resolver.resolve')
@patch('app.intelligence.infrastructure.get_domain_rdap')
@patch('app.intelligence.infrastructure.get_ip_rdap')
@patch('app.intelligence.infrastructure.get_tls_summary')
@patch('app.intelligence.infrastructure.fetch_website_safely')
async def test_investigate_infrastructure_lifetime_timeout_partial(mock_fetch, mock_tls, mock_ip_rdap, mock_dom_rdap, mock_resolve):
    mock_resolve.side_effect = dns.resolver.LifetimeTimeout()

    mock_dom_rdap.return_value = ({"registrar": "Test"}, False)
    mock_ip_rdap.return_value = ({}, False)
    mock_tls.return_value = (None, False)
    mock_fetch.return_value = {"html": "<html><script src='googletagmanager.com/gtm.js'></script></html>", "headers": {}}
    
    res = await investigate_infrastructure("sabic.com")
    assert res["status"] == "partial"


@pytest.mark.anyio
@patch('app.intelligence.infrastructure.resolve_dns')
@patch('app.intelligence.infrastructure.get_domain_rdap')
@patch('app.intelligence.infrastructure.get_ip_rdap')
@patch('app.intelligence.infrastructure.get_tls_summary')
@patch('app.intelligence.infrastructure.fetch_website_safely')
async def test_investigate_infrastructure_tls_failure(mock_fetch, mock_tls, mock_ip_rdap, mock_dom_rdap, mock_dns):
    mock_dns.return_value = ({"A": ["8.8.8.8"], "AAAA": [], "MX": [], "NS": []}, False)
    mock_dom_rdap.return_value = ({}, False)
    mock_ip_rdap.return_value = ({}, False)
    mock_tls.return_value = (None, True)
    mock_fetch.return_value = {"html": "<html></html>", "headers": {}}
    
    res = await investigate_infrastructure("sabic.com")
    assert res["status"] == "partial"

@pytest.mark.anyio
@patch('app.intelligence.infrastructure.resolve_dns')
@patch('app.intelligence.infrastructure.get_domain_rdap')
@patch('app.intelligence.infrastructure.get_ip_rdap')
@patch('app.intelligence.infrastructure.get_tls_summary')
@patch('app.intelligence.infrastructure.fetch_website_safely')
async def test_investigate_infrastructure_rdap_failure(mock_fetch, mock_tls, mock_ip_rdap, mock_dom_rdap, mock_dns):
    mock_dns.return_value = ({"A": ["8.8.8.8"], "AAAA": [], "MX": [], "NS": []}, False)
    mock_dom_rdap.return_value = ({}, True)
    mock_ip_rdap.return_value = ({}, False)
    mock_tls.return_value = (None, False)
    mock_fetch.return_value = {"html": "<html></html>", "headers": {}}
    
    res = await investigate_infrastructure("sabic.com")
    assert res["status"] == "partial"

@pytest.mark.anyio
@patch('app.intelligence.infrastructure.resolve_dns')
@patch('app.intelligence.infrastructure.get_domain_rdap')
@patch('app.intelligence.infrastructure.get_ip_rdap')
@patch('app.intelligence.infrastructure.get_tls_summary')
@patch('app.intelligence.infrastructure.fetch_website_safely')
async def test_investigate_infrastructure_fetch_failure(mock_fetch, mock_tls, mock_ip_rdap, mock_dom_rdap, mock_dns):
    mock_dns.return_value = ({"A": ["8.8.8.8"], "AAAA": [], "MX": [], "NS": []}, False)
    mock_dom_rdap.return_value = ({}, False)
    mock_ip_rdap.return_value = ({}, False)
    mock_tls.return_value = (None, False)
    mock_fetch.side_effect = Exception("Fetch failed")
    
    res = await investigate_infrastructure("sabic.com")
    assert res["status"] == "partial"

@pytest.mark.anyio
@patch('app.intelligence.infrastructure.resolve_dns')
@patch('app.intelligence.infrastructure.get_domain_rdap')
@patch('app.intelligence.infrastructure.get_ip_rdap')
@patch('app.intelligence.infrastructure.get_tls_summary')
@patch('app.intelligence.infrastructure.fetch_website_safely')
async def test_investigate_infrastructure_unavailable(mock_fetch, mock_tls, mock_ip_rdap, mock_dom_rdap, mock_dns):
    mock_dns.return_value = ({"A": [], "AAAA": [], "MX": [], "NS": []}, True)
    mock_dom_rdap.return_value = ({}, True)
    mock_ip_rdap.return_value = ({}, True)
    mock_tls.return_value = (None, True)
    mock_fetch.side_effect = Exception("Fetch failed")
    
    res = await investigate_infrastructure("sabic.com")
    assert res["status"] == "unavailable"
