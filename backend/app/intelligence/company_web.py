import httpx
import socket
import ipaddress
from urllib.parse import urlparse, urljoin
import re
import logging
from app.models.company import Company
from app.models.intelligence import Evidence, IntelligenceEntity

logger = logging.getLogger(__name__)

class SafetyException(Exception):
    pass

def check_url_safety(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SafetyException("Invalid scheme")
    if not parsed.hostname:
        raise SafetyException("Invalid hostname")
    try:
        for res in socket.getaddrinfo(parsed.hostname, None):
            ip = res[4][0]
            ip_obj = ipaddress.ip_address(ip)
            if not ip_obj.is_global:
                raise SafetyException("Unsafe IP destination")
    except socket.gaierror:
        raise SafetyException("DNS resolution failed")
    except ValueError:
        pass

async def fetch_website_safely(url: str) -> dict:
    max_redirects = 3
    timeout = 5.0
    current_url = url
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            check_url_safety(current_url)
            
            try:
                async with client.stream("GET", current_url) as response:
                    if 300 <= response.status_code < 400:
                        location = response.headers.get("location")
                        if not location:
                            break
                        current_url = urljoin(current_url, location)
                        continue
                    
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" not in content_type:
                        raise SafetyException(f"Invalid content type: {content_type}")
                    
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > 512 * 1024:
                        raise SafetyException("Response too large")
                    
                    body = b""
                    async for chunk in response.aiter_bytes():
                        body += chunk
                        if len(body) > 512 * 1024:
                            raise SafetyException("Response body exceeded 512KB")
                    
                    return {
                        "final_url": current_url,
                        "status_code": response.status_code,
                        "html": body.decode("utf-8", errors="ignore")
                    }
            except httpx.RequestError as e:
                raise SafetyException(f"Request failed: {str(e)}")
                
        raise SafetyException("Too many redirects")

def extract_html_info(html: str) -> dict:
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else None
    
    meta_desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
    meta_desc = meta_desc_match.group(1).strip() if meta_desc_match else None
    
    canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']', html, re.IGNORECASE)
    canonical = canonical_match.group(1).strip() if canonical_match else None
    
    lang_match = re.search(r'<html[^>]*lang=["\'](.*?)["\']', html, re.IGNORECASE)
    lang = lang_match.group(1).strip() if lang_match else None
    
    emails = list(set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html)))
    
    phones = list(set(re.findall(r'(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}', html)))
    phones = list(set([p.strip() for p in phones if len(re.sub(r'\D', '', p)) >= 8]))
    
    social_pattern = r'href=["\'](https?://(?:www\.)?(?:linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|youtube\.com)/[^"\']+)["\']'
    social_links = list(set(re.findall(social_pattern, html, re.IGNORECASE)))
    
    return {
        "title": title,
        "meta_description": meta_desc,
        "canonical_url": canonical,
        "language": lang,
        "emails": emails,
        "phones": phones,
        "social_links": social_links
    }

async def investigate_website(website_url: str, company: Company, entities: list, relationships: list):
    try:
        if not website_url.startswith("http"):
            website_url = "https://" + website_url
            
        result = await fetch_website_safely(website_url)
        info = extract_html_info(result["html"])
        
        final_url = result["final_url"]
        
        company.website = final_url
        evidence = Evidence(source="Company Website", source_url=final_url)
        company.evidence.append(evidence)
        
        if not hasattr(company, "attributes") or company.attributes is None:
            company.attributes = {}
            
        company.attributes["web_intelligence"] = {
            "http_status": result["status_code"],
            "title": info["title"],
            "meta_description": info["meta_description"],
            "canonical_url": info["canonical_url"],
            "language": info["language"],
        }
        
        for email in info["emails"]:
            entities.append(IntelligenceEntity(
                id=f"email_{email}",
                type="email",
                label=email,
                evidence=[Evidence(source="Company Website", source_url=final_url)]
            ))
            
        for phone in info["phones"]:
            entities.append(IntelligenceEntity(
                id=f"phone_{phone}",
                type="phone",
                label=phone,
                evidence=[Evidence(source="Company Website", source_url=final_url)]
            ))
            
        for link in info["social_links"]:
            entities.append(IntelligenceEntity(
                id=f"social_{link}",
                type="social_profile",
                label=link,
                evidence=[Evidence(source="Company Website", source_url=final_url)]
            ))
            
    except Exception as e:
        logger.warning(f"Website investigation failed: {e}")
        if not hasattr(company, "attributes") or company.attributes is None:
            company.attributes = {}
        company.attributes["web_intelligence_error"] = str(e)
