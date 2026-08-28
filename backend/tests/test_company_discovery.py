import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.intelligence.company_discovery import score_candidate, discover_website
from app.models.company import Company

def test_score_candidate():
    score1 = score_candidate("https://www.saudiaramco.com/", "Saudi Aramco Official", "The official site", "Saudi Aramco")
    assert score1 >= 5 
    
    score2 = score_candidate("https://www.linkedin.com/company/saudiaramco", "Saudi Aramco LinkedIn", "LinkedIn profile", "Saudi Aramco")
    assert score2 < 0 
    
    score3 = score_candidate("https://example.com/article", "News Article", "Some news about saudi aramco", "Saudi Aramco")
    assert score3 == 2 

    # Apex/Root vs Service Subdomain
    score_apex = score_candidate("https://emiratesnbd.com/", "Emirates NBD", "Bank", "Emirates NBD")
    score_sub = score_candidate("https://businessonline.emiratesnbd.com/", "Emirates NBD Business", "Portal", "Emirates NBD")
    assert score_apex > score_sub

    # Service Subdomain alone can still be positive
    assert score_sub > 0

    # Regional domains and tldextract tests
    score_sa_root = score_candidate("https://example.com.sa/", "Example", "SA Root", "Example")
    score_sa_sub = score_candidate("https://login.example.com.sa/", "Example Login", "SA Login", "Example")
    assert score_sa_root > score_sa_sub
    assert score_sa_root >= 2 # apex bonus + 2
    
    score_ae_root = score_candidate("https://example.ae/", "Example", "AE Root", "Example")
    assert score_ae_root >= 2

    score_sa_www = score_candidate("https://www.example.com.sa/", "Example", "SA WWW", "Example")
    assert score_sa_www == score_sa_root

def test_discover_website_mocked_success():
    company = Company(name="Test Corp", normalized_name="test corp")
    
    mock_html = """
    <div class="result results_links">
        <h2 class="result__title"><a href="https://testcorp.com">Test Corp Official</a></h2>
        <a class="result__url" href="https://testcorp.com">testcorp.com</a>
        <a class="result__snippet">Welcome to Test Corp.</a>
    </div>
    <div class="result results_links">
        <h2 class="result__title"><a href="https://linkedin.com/testcorp">LinkedIn</a></h2>
        <a class="result__url" href="https://linkedin.com/testcorp">linkedin.com</a>
        <a class="result__snippet">Social profile</a>
    </div>
    """
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.text = mock_html
        mock_post.return_value.raise_for_status = lambda: None
        
        result = asyncio.run(discover_website(company, "Test Corp"))
        assert result == "https://testcorp.com"
        assert company.attributes["discovery"]["confidence"] == "high"
        assert len(company.attributes["discovery"]["candidates"]) == 2
        assert company.attributes["discovery"]["candidates"][0]["url"] == "https://testcorp.com"

def test_discover_website_search_failure():
    company = Company(name="Test Corp", normalized_name="test corp")
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Timeout")
        
        result = asyncio.run(discover_website(company, "Test Corp"))
        assert result is None
        assert "Timeout" in company.attributes["discovery_error"]

def test_discover_website_weak_results():
    company = Company(name="Unknown Corp", normalized_name="unknown corp")
    
    mock_html = """
    <div class="result results_links">
        <h2 class="result__title"><a href="https://some-blog.com/post">Some Blog</a></h2>
        <a class="result__url" href="https://some-blog.com/post">some-blog.com</a>
        <a class="result__snippet">Mentioning unknown corp.</a>
    </div>
    """
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.text = mock_html
        mock_post.return_value.raise_for_status = lambda: None
        
        result = asyncio.run(discover_website(company, "Unknown Corp"))
        assert result is None
        assert company.attributes["discovery"]["confidence"] == "low"
