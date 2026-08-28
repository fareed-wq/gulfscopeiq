import httpx
import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from app.models.company import Company
from app.models.intelligence import Evidence, IntelligenceEntity, IntelligenceRelationship

logger = logging.getLogger(__name__)

def evaluate_relevance(title: str, normalized_name: str) -> str | None:
    t_lower = title.lower()
    c_lower = normalized_name
    if not c_lower:
        return None
        
    if c_lower in t_lower:
        return "high"
        
    stop_words = {
        "saudi", "arabia", "uae", "emirates", "dubai", "qatar", "oman", 
        "bahrain", "kuwait", "company", "group", "holding", "holdings", 
        "bank", "national", "international", "limited", "ltd", "llc", 
        "inc", "corporation", "corp", "the", "and"
    }
    
    words = [w for w in c_lower.split() if w not in stop_words and len(w) >= 3]
    if words:
        for w in words:
            if w in t_lower:
                return "medium"
        
    return None

async def discover_news(company: Company, entities: list[IntelligenceEntity], relationships: list[IntelligenceRelationship]):
    query = quote_plus(company.name)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            if len(response.text) > 1024 * 1024:
                raise ValueError("RSS feed too large")
                
            xml_data = response.text
    except Exception as e:
        company.attributes["news_error"] = str(e)
        return
        
    try:
        root = ET.fromstring(xml_data)
        channel = root.find("channel")
        if channel is None:
            return
            
        items = channel.findall("item")
        seen_urls = set()
        seen_titles = set()
        count = 0
        
        for item in items:
            if count >= 10:
                break
                
            title_node = item.find("title")
            link_node = item.find("link")
            pub_date_node = item.find("pubDate")
            source_node = item.find("source")
            
            if title_node is None or link_node is None:
                continue
                
            title = title_node.text
            link = link_node.text
            
            if not title or not link:
                continue
                
            publisher = source_node.text if source_node is not None else None
            published_at = pub_date_node.text if pub_date_node is not None else None
            
            if link in seen_urls or title in seen_titles:
                continue
                
            confidence = evaluate_relevance(title, company.normalized_name)
            if not confidence:
                continue
                
            seen_urls.add(link)
            seen_titles.add(title)
            count += 1
            
            evidence = Evidence(
                source="Google News RSS",
                source_url=url,
                excerpt=title
            )
            
            article_id = f"news_{abs(hash(link))}"
            
            entity = IntelligenceEntity(
                id=article_id,
                type="news_article",
                label=title,
                attributes={
                    "url": link,
                    "publisher": publisher,
                    "published_at": published_at,
                    "confidence": confidence
                },
                evidence=[evidence]
            )
            entities.append(entity)
            
            # Since relationship source needs an ID, and we don't have a formal entity ID for the company yet,
            # we use the company's normalized name as a placeholder root ID
            company_root_id = company.normalized_name
            relationships.append(IntelligenceRelationship(
                source=company_root_id,
                target=article_id,
                type="mentioned_in",
                confidence=confidence,
                evidence=[evidence]
            ))
            
    except Exception as e:
        company.attributes["news_parse_error"] = str(e)
