from typing import Tuple, List, Optional
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
import re
from app.models.tender import Tender
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship, Evidence

BASE_URL = "https://capt.gov.kw/en/tenders/opening-tenders/"

COVERAGE_NOTE = (
    "Kuwait search covers up to 40 recent CAPT opening tenders "
    "and is not an exhaustive archive search."
)


class DownloadTooLargeError(Exception):
    pass


async def _fetch_with_cap(session: AsyncSession, url: str, **kwargs):
    """GET with a hard 5 MB streaming download cap."""
    cap = 5 * 1024 * 1024
    total = 0
    body = bytearray()

    def cb(chunk):
        nonlocal total
        total += len(chunk)
        if total > cap:
            raise DownloadTooLargeError(f"Response exceeded {cap} bytes limit")
        body.extend(chunk)

    res = await session.request("GET", url, content_callback=cb, **kwargs)
    res.content = bytes(body)
    return res


def _parse_tenders_from_html(html: str) -> list[dict]:
    """Parse CAPT opening-tenders HTML into a list of raw tender dicts."""
    soup = BeautifulSoup(html, "html.parser")
    tlist = soup.find("div", class_="tenderslist")
    if not tlist:
        return []

    items = tlist.find_all("div", class_="content-box", recursive=False)
    results = []
    for item in items:
        tender_data: dict = {}

        # Tender number + date
        tenderno_p = item.find("p", class_="tenderno")
        if tenderno_p:
            span = tenderno_p.find("span")
            if span:
                tender_data["published_at"] = span.get_text(strip=True)
                span.decompose()
            tender_data["reference_number"] = tenderno_p.get_text(strip=True)

        # Authority
        orgname_p = item.find("p", class_="orgname")
        if orgname_p:
            tender_data["authority"] = orgname_p.get_text(strip=True)

        # Title – second <p> inside tender-detail
        detail_div = item.find("div", class_="tender-detail")
        if detail_div:
            ps = detail_div.find_all("p")
            if len(ps) > 1:
                tender_data["title"] = ps[1].get_text(strip=True)
            elif ps:
                tender_data["title"] = ps[0].get_text(strip=True)

        if tender_data.get("title") or tender_data.get("reference_number"):
            results.append(tender_data)

    return results


def _matches_query(tender_data: dict, query: str) -> bool:
    """Case-insensitive local keyword match against title and authority."""
    q = query.lower()
    title = (tender_data.get("title") or "").lower()
    authority = (tender_data.get("authority") or "").lower()
    return q in title or q in authority


async def search_kuwait_tenders(
    query: str,
    session: Optional[AsyncSession] = None,
) -> Tuple[List[Tender], List[IntelligenceEntity], List[IntelligenceRelationship]]:
    tenders: list[Tender] = []
    entities: list[IntelligenceEntity] = []
    relationships: list[IntelligenceRelationship] = []

    close_session = False
    if session is None:
        session = AsyncSession(impersonate="chrome110")
        close_session = True

    try:
        # Fetch page 1
        res1 = await _fetch_with_cap(session, BASE_URL, timeout=8.0)
        all_rows = _parse_tenders_from_html(res1.text)

        # Fetch page 2 only if page 1 returned a full page of 20
        if len(all_rows) >= 20:
            res2 = await _fetch_with_cap(
                session, BASE_URL + "?page=2", timeout=8.0
            )
            all_rows.extend(_parse_tenders_from_html(res2.text))

        # Hard cap: inspect at most 40 rows
        all_rows = all_rows[:40]

        # Local keyword filtering
        matched = [r for r in all_rows if _matches_query(r, query)]

        # Cap results at 20
        matched = matched[:20]

        seen_orgs: set[str] = set()

        for row in matched:
            title = row.get("title") or f"Kuwait CAPT Tender {row.get('reference_number', 'Unknown')}"
            ref = row.get("reference_number")
            authority = row.get("authority")
            published = row.get("published_at")
            source_url = BASE_URL

            evidence = Evidence(
                source="Kuwait CAPT Public Portal",
                source_url=source_url,
                excerpt=f"{ref or ''} - {title}"[:200],
            )

            tender = Tender(
                title=title,
                reference_number=ref,
                issuing_authority=authority,
                published_at=published,
                country_code="KW",
                status="opening",
                source_url=source_url,
                evidence=[evidence],
                attributes={"coverage_note": COVERAGE_NOTE},
            )
            tenders.append(tender)

            t_entity = IntelligenceEntity(
                id=f"kw_tender_{ref or hash(title)}",
                type="tender",
                label=title,
                evidence=[evidence],
            )
            entities.append(t_entity)

            if authority:
                org_id = f"org_kw_{hash(authority)}"
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
                    source=f"kw_tender_{ref or hash(title)}",
                    target=org_id,
                    type="issued_by",
                    confidence="medium",
                    evidence=[evidence],
                )
                relationships.append(rel)

    except DownloadTooLargeError:
        pass
    except Exception:
        pass
    finally:
        if close_session:
            pass

    return tenders, entities, relationships
