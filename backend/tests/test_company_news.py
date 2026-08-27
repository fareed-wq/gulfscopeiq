import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.models.company import Company
from app.intelligence.company_news import discover_news

def test_discover_news_success():
    company = Company(name="Saudi Aramco", normalized_name="saudi aramco")
    entities = []
    relationships = []
    
    mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Saudi Aramco announces record profits</title>
                <link>https://example.com/news/1</link>
                <pubDate>Thu, 01 Jan 2026 00:00:00 GMT</pubDate>
                <source>Financial News</source>
            </item>
            <item>
                <title>Saudi Aramco announces record profits</title>
                <link>https://example.com/news/1</link>
                <pubDate>Thu, 01 Jan 2026 00:00:00 GMT</pubDate>
                <source>Financial News</source>
            </item>
            <item>
                <title>Unrelated article about tech</title>
                <link>https://example.com/news/2</link>
                <pubDate>Thu, 01 Jan 2026 01:00:00 GMT</pubDate>
                <source>Tech Blog</source>
            </item>
            <item>
                <title>Aramco secures new deals</title>
                <link>https://example.com/news/3</link>
                <pubDate>Thu, 01 Jan 2026 02:00:00 GMT</pubDate>
                <source>Oil Daily</source>
            </item>
        </channel>
    </rss>
    """
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.text = mock_rss
        mock_get.return_value.raise_for_status = lambda: None
        
        asyncio.run(discover_news(company, entities, relationships))
        
        # 3 unique relevant articles expected: 1 exact, 1 medium, 1 filtered out
        # Actually, "Aramco secures new deals" has "aramco" which is length 6 and matches "saudi aramco".
        
        news_entities = [e for e in entities if e.type == "news_article"]
        assert len(news_entities) == 2
        
        # Check first article (exact match)
        assert news_entities[0].label == "Saudi Aramco announces record profits"
        assert news_entities[0].attributes["confidence"] == "high"
        
        # Check second article (partial match)
        assert news_entities[1].label == "Aramco secures new deals"
        assert news_entities[1].attributes["confidence"] == "medium"
        
        # Check relationships
        assert len(relationships) == 2
        assert relationships[0].type == "mentioned_in"
        assert relationships[0].source == "saudi aramco"
        assert relationships[0].target == news_entities[0].id

def test_evaluate_relevance():
    from app.intelligence.company_news import evaluate_relevance
    # Saudi-only headline rejected for Saudi Aramco
    assert evaluate_relevance("Saudi Arabia announces new tech fund", "saudi aramco") is None
    # Aramco headline accepted
    assert evaluate_relevance("Aramco invests in tech", "saudi aramco") == "medium"
    # Emirates-only headline rejected for Emirates NBD
    assert evaluate_relevance("Emirates Airlines launches new route", "emirates nbd") is None
    # Emirates NBD exact headline accepted
    assert evaluate_relevance("Emirates NBD reports earnings", "emirates nbd") == "high"

def test_discover_news_malformed_xml():
    company = Company(name="Test Corp", normalized_name="test corp")
    entities = []
    relationships = []
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.text = "<not_xml>"
        mock_get.return_value.raise_for_status = lambda: None
        
        asyncio.run(discover_news(company, entities, relationships))
        
        assert len(entities) == 0
        assert "news_parse_error" in company.attributes

def test_discover_news_network_failure():
    company = Company(name="Test Corp", normalized_name="test corp")
    entities = []
    relationships = []
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Connection Timeout")
        
        asyncio.run(discover_news(company, entities, relationships))
        
        assert len(entities) == 0
        assert "Connection Timeout" in company.attributes.get("news_error", "")
