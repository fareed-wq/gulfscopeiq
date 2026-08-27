import pytest
from unittest.mock import patch, AsyncMock
from app.intelligence.company_web import extract_html_info, investigate_website, check_url_safety, SafetyException
from app.models.company import Company

def test_extract_html_info():
    html = """
    <html lang="en">
    <head>
        <title>Test Company</title>
        <meta name="description" content="A great company">
        <link rel="canonical" href="https://example.com">
    </head>
    <body>
        Contact us at info@example.com or +1 800 555 1234.
        <a href="https://linkedin.com/company/test">LinkedIn</a>
    </body>
    </html>
    """
    info = extract_html_info(html)
    assert info["title"] == "Test Company"
    assert info["meta_description"] == "A great company"
    assert info["canonical_url"] == "https://example.com"
    assert info["language"] == "en"
    assert "info@example.com" in info["emails"]
    assert "+1 800 555 1234" in info["phones"]
    assert "https://linkedin.com/company/test" in info["social_links"]

import asyncio

def test_investigate_website_mocked():
    company = Company(name="Test", normalized_name="test")
    entities = []
    relationships = []
    
    with patch("app.intelligence.company_web.fetch_website_safely", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {
            "final_url": "https://example.com",
            "status_code": 200,
            "html": "<title>Mock</title>"
        }
        asyncio.run(investigate_website("example.com", company, entities, relationships))
        
        assert company.website == "https://example.com"
        assert len(company.evidence) == 1
        assert company.evidence[0].source_url == "https://example.com"
        assert company.attributes["web_intelligence"]["title"] == "Mock"

def test_investigate_website_failure_isolation():
    company = Company(name="Test", normalized_name="test")
    entities = []
    relationships = []
    
    with patch("app.intelligence.company_web.fetch_website_safely", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = SafetyException("Blocked")
        asyncio.run(investigate_website("example.com", company, entities, relationships))
        
        assert "Blocked" in company.attributes["web_intelligence_error"]


def test_check_url_safety_private():
    with pytest.raises(SafetyException, match="Unsafe IP"):
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, '', ('127.0.0.1', 80))]
            check_url_safety("http://localhost")

    with pytest.raises(SafetyException, match="Unsafe IP"):
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, '', ('10.0.0.1', 80))]
            check_url_safety("http://private")

    with pytest.raises(SafetyException, match="Unsafe IP"):
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(23, 1, 6, '', ('::1', 80, 0, 0))]
            check_url_safety("http://ipv6-local")

    with pytest.raises(SafetyException, match="Unsafe IP"):
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, '', ('0.0.0.0', 80))]
            check_url_safety("http://unspecified")

    with pytest.raises(SafetyException, match="Unsafe IP"):
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, '', ('8.8.8.8', 80)),
                (2, 1, 6, '', ('192.168.1.1', 80))
            ]
            check_url_safety("http://mixed")

    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, '', ('8.8.8.8', 80))]
        check_url_safety("http://safe")
