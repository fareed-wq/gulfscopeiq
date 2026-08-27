from typing import Tuple, List, Optional
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
import re
import urllib.parse
from app.models.tender import Tender
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship, Evidence
from app.core.tls_trust import get_qatar_mof_ca_bundle

BASE_URL = "https://monaqasat.mof.gov.qa/TendersOnlineServices/AvailableMinistriesTenders/1"
BASE_DOMAIN = "https://monaqasat.mof.gov.qa"

class DownloadTooLargeError(Exception):
    pass

async def _fetch_with_cap(session: AsyncSession, method: str, url: str, **kwargs):
    cap = 5 * 1024 * 1024  # 5MB
    total = 0
    body = bytearray()
    
    def cb(chunk):
        nonlocal total
        total += len(chunk)
        if total > cap:
            raise DownloadTooLargeError(f"Response exceeded {cap} bytes limit")
        body.extend(chunk)
        
    res = await session.request(method, url, content_callback=cb, **kwargs)
    res.content = bytes(body)
    return res

async def search_qatar_tenders(query: str, session: Optional[AsyncSession] = None) -> Tuple[List[Tender], List[IntelligenceEntity], List[IntelligenceRelationship]]:
    tenders = []
    entities = []
    relationships = []
    
    close_session = False
    if session is None:
        session = AsyncSession(impersonate="chrome110", verify=get_qatar_mof_ca_bundle())
        close_session = True
        
    try:
        # 1. GET Request
        res_get = await _fetch_with_cap(session, "GET", BASE_URL, timeout=8.0)
            
        soup = BeautifulSoup(res_get.text, "html.parser")
        token_input = soup.find("input", {"name": "__RequestVerificationToken"})
        if not token_input or not token_input.get("value"):
            return [], [], []
            
        token = token_input["value"]
        
        # 2. POST Request
        data = {
            "__RequestVerificationToken": token,
            "SearchData.TenderSubject": query
        }
        res_post = await _fetch_with_cap(session, "POST", BASE_URL, data=data, timeout=8.0)
            
        soup2 = BeautifulSoup(res_post.text, "html.parser")
        
        # Extract rows
        detail_links = soup2.find_all("a", href=lambda h: h and "/TendersOnlineServices/TenderDetails/" in h)
        if not detail_links:
            # Fallback to GET response if POST fails or returns empty unexpectedly
            detail_links = soup.find_all("a", href=lambda h: h and "/TendersOnlineServices/TenderDetails/" in h)
            
        seen_urls = set()
        seen_orgs = set()
        
        for a_tag in detail_links[:20]:
            href = a_tag["href"]
            source_url = urllib.parse.urljoin(BASE_DOMAIN, href)
            
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            
            parent = a_tag.find_parent("div", class_="row")
            if not parent:
                parent = a_tag.find_parent("div") or a_tag
                
            raw_text = re.sub(r'\s+', ' ', parent.get_text()).strip()
            
            title = a_tag.get_text(strip=True)
            if not title:
                title = f"Qatar MOF Tender {href.split('/')[-1]}"
                
            ref_number = None
            ref_match = re.search(r'(\d+/\d{4})', raw_text)
            if ref_match:
                ref_number = ref_match.group(1)
                
            deadline = None
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', raw_text)
            if date_match:
                deadline = date_match.group(1)
                
            authority = None
            
            evidence = Evidence(
                source="Qatar MOF Public Portal",
                source_url=source_url,
                excerpt=raw_text[:200]
            )
            
            tender = Tender(
                title=title,
                reference_number=ref_number,
                deadline=deadline,
                country_code="QA",
                status="available",
                source_url=source_url,
                description=raw_text,
                evidence=[evidence]
            )
            tenders.append(tender)
            
            t_entity = IntelligenceEntity(
                id=source_url,
                type="tender",
                label=title,
                evidence=[evidence]
            )
            entities.append(t_entity)
            
            if authority:
                org_id = f"org_qa_{hash(authority)}"
                if org_id not in seen_orgs:
                    seen_orgs.add(org_id)
                    org_entity = IntelligenceEntity(
                        id=org_id,
                        type="organization",
                        label=authority,
                        evidence=[evidence]
                    )
                    entities.append(org_entity)
                    
                rel = IntelligenceRelationship(
                    source=source_url,
                    target=org_id,
                    type="issued_by",
                    confidence="medium",
                    evidence=[evidence]
                )
                relationships.append(rel)
                tender.issuing_authority = authority
                
    except DownloadTooLargeError:
        # Expected limit, return empty or partial
        pass
    except Exception:
        # Isolated network or parse failure
        pass
    finally:
        if close_session:
            pass
            
    return tenders, entities, relationships
