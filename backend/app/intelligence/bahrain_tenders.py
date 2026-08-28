import httpx
import json
import traceback
from typing import Tuple, List, Optional
from bs4 import BeautifulSoup
from app.models.tender import Tender
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship, Evidence

BASE_URL = "https://www.tenderboard.gov.bh"
ENDPOINT_URL = "https://www.tenderboard.gov.bh/Templates/TenderBoardWebService.aspx/GetCurrentPublicTenderByPage"

class DownloadTooLargeError(Exception):
    pass

async def _post_with_cap(client: httpx.AsyncClient, url: str, payload: dict, timeout: float = 8.0) -> dict:
    """POST with a hard 5 MB streaming download cap."""
    cap = 5 * 1024 * 1024
    total = 0
    body = bytearray()

    async with client.stream(
        "POST", 
        url, 
        json=payload, 
        headers={"User-Agent": "Mozilla/5.0"}, 
        timeout=timeout
    ) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > cap:
                raise DownloadTooLargeError(f"Response exceeded {cap} bytes limit")
            body.extend(chunk)

    decoded = body.decode("utf-8")
    return json.loads(decoded)

def _parse_tenders_from_html(html: str) -> list[dict]:
    """Parse Bahrain Tender Board HTML into a list of raw tender dicts."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("div", class_="rows")
    results = []
    
    for row in rows:
        tender_data = {}
        cols = row.find_all("div", class_="column")
        for col in cols:
            label = col.get("data-label")
            text = col.get_text(strip=True)
            if not label:
                continue
                
            if label == "No./Tender Subject":
                a_tag = col.find("a")
                if a_tag:
                    span_tag = a_tag.find("span")
                    if span_tag:
                        tender_data["reference_number"] = span_tag.get_text(strip=True)
                        span_tag.decompose()
                    tender_data["title_raw"] = a_tag.get_text(strip=True)
                else:
                    tender_data["title_raw"] = text
            elif label == "Tender Type":
                tender_data["tender_type"] = text
            elif label == "Purchasing Authority":
                tender_data["authority"] = text
            elif label == "Publish Date":
                tender_data["published_at"] = text
            elif label == "Purchase Before":
                tender_data["purchase_before"] = text
            elif label == "Closing Date":
                tender_data["deadline"] = text
                
        # Extract link
        a_tag = row.find("a", href=True)
        if a_tag:
            href = a_tag["href"]
            if href.startswith("/"):
                tender_data["source_url"] = BASE_URL + href
            else:
                tender_data["source_url"] = href
                
        if tender_data.get("title_raw"):
            results.append(tender_data)
            
    return results

def _build_payload(query: str, page: int) -> dict:
    return {
        "tenderNumber": query,
        "ministry": "0",
        "category": "0",
        "tendertype": "0",
        "closingDate_filter": "",
        "publicTenderOnly": "false",
        "prequalificationOnly": "false",
        "auctionOnly": "false",
        "sortingType": "1",
        "listPage": "mainList",
        "Page": str(page),
        "smeTendersOnly": "false",
        "sectionName": ""
    }

async def search_bahrain_tenders(
    query: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Tuple[List[Tender], List[IntelligenceEntity], List[IntelligenceRelationship]]:
    tenders: list[Tender] = []
    entities: list[IntelligenceEntity] = []
    relationships: list[IntelligenceRelationship] = []

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True

    try:
        # Fetch page 1
        payload1 = _build_payload(query, 1)
        res1 = await _post_with_cap(client, ENDPOINT_URL, payload1, timeout=8.0)
        html1 = res1.get("d", "")
        all_rows = _parse_tenders_from_html(html1)

        # If page 1 returns full 10 results, fetch page 2
        if len(all_rows) >= 10:
            payload2 = _build_payload(query, 2)
            res2 = await _post_with_cap(client, ENDPOINT_URL, payload2, timeout=8.0)
            html2 = res2.get("d", "")
            all_rows.extend(_parse_tenders_from_html(html2))

        # Cap results at 20
        all_rows = all_rows[:20]

        seen_orgs: set[str] = set()

        for row in all_rows:
            raw_title = row.get("title_raw", "Bahrain Tender")
            authority = row.get("authority")
            source_url = row.get("source_url") or f"{BASE_URL}/Tenders/PublicTenders/"
            
            # The title and ref might be glued together or not. 
            # We'll put the raw string in title. 
            # If the user wants specific ref, we don't have a reliable split delimiter,
            # so we map the whole thing to title and leave ref blank to avoid false parses.
            # But wait, looking at the previous investigation: 
            # `TRA/INTERNAL/RFP/2025/005Telecom Security Drill Exercise`
            # Often the ID is `TRA/INTERNAL/RFP/2025/005` and title is `Telecom Security Drill Exercise`.
            # We will just map it all to title.
            
            title = raw_title
            ref = row.get("reference_number")
            
            evidence = Evidence(
                source="Bahrain Tender Board",
                source_url=source_url,
                excerpt=title[:200],
            )
            
            attrs = {}
            if row.get("purchase_before"):
                attrs["purchase_before"] = row.get("purchase_before")
            if row.get("tender_type"):
                attrs["tender_type"] = row.get("tender_type")
                
            # Note: "status" is strictly left unset as per instructions unless explicitly supported.
            
            tender = Tender(
                title=title,
                reference_number=ref,
                issuing_authority=authority,
                published_at=row.get("published_at"),
                deadline=row.get("deadline"),
                country_code="BH",
                source_url=source_url,
                evidence=[evidence],
                attributes=attrs if attrs else None,
            )
            tenders.append(tender)

            # Entity for tender
            t_id = f"bh_tender_{hash(source_url + title)}"
            t_entity = IntelligenceEntity(
                id=t_id,
                type="tender",
                label=title,
                evidence=[evidence],
            )
            entities.append(t_entity)

            # Organization and relationship
            if authority:
                org_id = f"org_bh_{hash(authority)}"
                if org_id not in seen_orgs:
                    seen_orgs.add(org_id)
                    org_entity = IntelligenceEntity(
                        id=org_id,
                        type="organization",
                        label=authority,
                        evidence=[evidence],
                    )
                    entities.append(org_entity)

                rel = IntelligenceRelationship(
                    source=t_id,
                    target=org_id,
                    type="issued_by",
                    confidence="high",
                    evidence=[evidence],
                )
                relationships.append(rel)

    except DownloadTooLargeError:
        pass
    except Exception as e:
        # Isolate malformed JSON/HTML/network failures
        # traceback.print_exc()
        pass
    finally:
        if close_client:
            await client.aclose()

    return tenders, entities, relationships
