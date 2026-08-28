import httpx
import re
import urllib.parse
from urllib.parse import urlparse
import logging
from app.models.company import Company

logger = logging.getLogger(__name__)

import tldextract

extract = tldextract.TLDExtract(suffix_list_urls=())

def score_candidate(url: str, title: str, snippet: str, company_name: str) -> int:
    score = 0
    parsed = urlparse(url)
    domain_full = parsed.netloc.lower()
    
    extracted = extract(domain_full)
    domain_for_name_check = extracted.top_domain_under_public_suffix or domain_full

    name_lower = company_name.lower()
    name_no_spaces = name_lower.replace(" ", "")

    penalized_domains = ["linkedin.com", "facebook.com", "twitter.com", "x.com", "wikipedia.org",
                         "bloomberg.com", "crunchbase.com", "glassdoor.com", "zoominfo.com",
                         "dnb.com", "yellowpages.com", "instagram.com", "youtube.com", "yahoo.com"]
    for pd in penalized_domains:
        if pd in domain_for_name_check:
            return -10 

    if not extracted.subdomain or extracted.subdomain == "www":
        score += 2

    service_keywords = ["login", "auth", "account", "portal", "businessonline", "onlinebanking", 
                        "ebanking", "secure", "app", "careers", "jobs", "support"]
    
    path_lower = parsed.path.lower()
    for keyword in service_keywords:
        if keyword in parsed.netloc.lower() or keyword in path_lower:
            score -= 3
            break

    if name_no_spaces and (name_no_spaces in domain_for_name_check or domain_for_name_check.startswith(name_no_spaces[:4])):
        score += 3
    
    if parsed.path in ("", "/"):
        score += 2
        
    if name_lower in title.lower():
        score += 1
        
    if "official" in title.lower() or "official" in snippet.lower():
        score += 2
        
    return score

async def discover_website(company: Company, company_name: str) -> str | None:
    timeout = 5.0
    search_url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                search_url,
                data={"q": f"{company_name} official website"},
                headers=headers
            )
            response.raise_for_status()
            html = response.text
            
            candidates = []
            
            blocks = html.split('<div class="result results_links')
            for block in blocks[1:11]:
                url_match = re.search(r'<a class="result__url" href="([^"]+)">', block)
                if not url_match:
                    continue
                url = url_match.group(1)
                
                if "uddg=" in url:
                    parsed = urlparse(url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    if "uddg" in qs:
                        url = qs["uddg"][0]
                
                title_match = re.search(r'<h2 class="result__title">.*?<a[^>]+>(.*?)</a>', block, re.DOTALL)
                title = title_match.group(1) if title_match else ""
                title = re.sub(r'<[^>]+>', '', title).strip()
                
                snippet_match = re.search(r'<a class="result__snippet[^>]*>(.*?)</a>', block, re.DOTALL)
                snippet = snippet_match.group(1) if snippet_match else ""
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                
                score = score_candidate(url, title, snippet, company_name)
                
                candidates.append({
                    "url": url,
                    "title": title,
                    "score": score
                })
            
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            best_website = None
            confidence = "low"
            
            if candidates:
                best = candidates[0]
                if best["score"] >= 5:
                    confidence = "high"
                    best_website = best["url"]
                elif best["score"] >= 3:
                    confidence = "medium"
                    best_website = best["url"]
            
            if not hasattr(company, "attributes") or company.attributes is None:
                company.attributes = {}
                
            company.attributes["discovery"] = {
                "website": best_website,
                "confidence": confidence,
                "source": "DuckDuckGo Search",
                "evidence": search_url,
                "candidates": candidates[:5]
            }
            
            return best_website
            
    except Exception as e:
        logger.warning(f"Website discovery failed: {e}")
        if not hasattr(company, "attributes") or company.attributes is None:
            company.attributes = {}
        company.attributes["discovery_error"] = str(e)
        return None
