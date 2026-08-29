import httpx
import asyncio
from typing import Tuple, List, Optional, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.models.job import Job
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship, Evidence

import hashlib

class DownloadTooLargeError(Exception):
    pass

def _stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"

SUCCESSFACTORS_SOURCES = {
    "Saudi Aramco": {
        "base_url": "https://careers.aramco.com",
        "aliases": ["aramco"],
        "country_code": "SA"
    },
    "STC": {
        "base_url": "https://careers.stc.com.sa",
        "aliases": ["saudi telecom company", "saudi telecom"],
        "country_code": "SA"
    },
    "SABIC": {
        "base_url": "https://jobs.sabic.com",
        "aliases": [],
        "country_code": "SA"
    },
    "OQ": {
        "base_url": "https://careers.oq.com",
        "aliases": ["oq", "oq energy"],
        "country_code": "OM"
    }
}

async def _get_with_cap(client: httpx.AsyncClient, url: str, timeout: float = 8.0) -> str:
    """GET with a hard 5 MB streaming download cap."""
    cap = 5 * 1024 * 1024
    total = 0
    body = bytearray()

    async with client.stream(
        "GET",
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout
    ) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > cap:
                raise DownloadTooLargeError(f"Response exceeded {cap} bytes limit")
            body.extend(chunk)

    return body.decode("utf-8", errors="replace")

def _parse_sf_jobs_html(html: str, base_url: str) -> List[Dict]:
    """Parse generic SuccessFactors (Jobs2Web) HTML rows."""
    soup = BeautifulSoup(html, "html.parser")

    # Validate expected SuccessFactors structure
    if not soup.find(class_="search-page") and not soup.find(class_="searchResultsShell") and not soup.find("table", class_="searchResults"):
        raise ValueError("Invalid SuccessFactors HTML structure (potential block page or source change)")

    rows = soup.find_all("tr", class_="data-row")
    results = []

    for row in rows[:25]:  # max 25 rows per employer
        job_data = {}

        # Title and URL
        a_tag = row.find("a", class_="jobTitle-link")
        if a_tag:
            job_data["title"] = a_tag.get_text(strip=True)
            href = a_tag.get("href")
            if href:
                job_data["source_url"] = urljoin(base_url, href)
        else:
            # Fallback if just span
            title_span = row.find("span", class_="jobTitle")
            if title_span:
                job_data["title"] = title_span.get_text(strip=True)

        # Location
        loc_span = row.find("span", class_="jobLocation")
        if loc_span:
            job_data["location"] = loc_span.get_text(strip=True)

        # Department
        dept_span = row.find("span", class_="jobDepartment")
        if dept_span:
            job_data["department"] = dept_span.get_text(strip=True)

        # Facility (subdepartment or ID)
        fac_span = row.find("span", class_="jobFacility")
        if fac_span:
            job_data["facility"] = fac_span.get_text(strip=True)

        # Date
        date_span = row.find("span", class_="jobDate")
        if date_span:
            job_data["published_at"] = date_span.get_text(strip=True)

        if job_data.get("title"):
            results.append(job_data)

    return results

async def _fetch_employer_jobs(
    client: httpx.AsyncClient,
    company_name: str,
    config: Dict,
    query: str
) -> Tuple[List[Job], bool]:
    base_url = config["base_url"]
    search_url = f"{base_url}/search/?q={query}&startrow=0"

    try:
        html = await _get_with_cap(client, search_url, timeout=8.0)
        parsed_rows = _parse_sf_jobs_html(html, base_url)

        jobs = []
        for row in parsed_rows:
            attrs = {}
            if "facility" in row:
                attrs["facility"] = row["facility"]

            evidence = Evidence(
                source=f"{company_name} Careers (SuccessFactors)",
                source_url=row.get("source_url") or search_url,
                excerpt=row.get("title", "")[:200]
            )

            job = Job(
                id=_stable_id("job_sf", row.get("source_url", search_url)),
                title=row.get("title", "Unknown Role"),
                company=company_name,
                location=row.get("location"),
                department=row.get("department"),
                published_at=row.get("date"),
                source_url=row.get("source_url") or search_url,
                evidence=[evidence],
                attributes=attrs
            )
            jobs.append(job)

        return jobs, True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"SuccessFactors job collector failed for {company_name}: {type(e).__name__} at {search_url}")
        return [], False

def _normalize_company(name: str) -> str:
    return " ".join(name.strip().lower().split())

def _match_sources(country_code: str, requested_company: Optional[str]) -> List[Tuple[str, Dict]]:
    matched = []

    for c_name, config in SUCCESSFACTORS_SOURCES.items():
        if config["country_code"] != country_code:
            continue

        if requested_company:
            req_norm = _normalize_company(requested_company)
            canonical_norm = _normalize_company(c_name)
            aliases_norm = [_normalize_company(a) for a in config["aliases"]]

            if req_norm == canonical_norm or req_norm in aliases_norm:
                matched.append((c_name, config))
        else:
            matched.append((c_name, config))

    return matched

async def search_successfactors_jobs(
    query: str,
    country_code: str,
    company: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None
) -> Tuple[List[Job], List[IntelligenceEntity], List[IntelligenceRelationship], str]:

    matched_sources = _match_sources(country_code, company)
    if not matched_sources:
        return [], [], [], "foundation"

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True

    # Max 3 external requests total
    matched_sources = matched_sources[:3]

    try:
        tasks = [
            _fetch_employer_jobs(client, name, config, query)
            for name, config in matched_sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        success_count = 0
        total_attempted = len(matched_sources)

        for res in results:
            if isinstance(res, Exception):
                continue
            jobs, success = res
            if success:
                success_count += 1
                all_jobs.extend(jobs)

        status = "collected"
        if success_count == 0:
            status = "error"
        elif success_count < total_attempted:
            status = "partial"

        # Deduplicate
        seen_urls = set()
        seen_fallback = set()
        deduped_jobs = []

        for j in all_jobs:
            if j.source_url:
                if j.source_url in seen_urls:
                    continue
                seen_urls.add(j.source_url)
            else:
                fb = f"{j.company}|{j.title}|{j.location}"
                if fb in seen_fallback:
                    continue
                seen_fallback.add(fb)

            deduped_jobs.append(j)

        # Cap at 30
        deduped_jobs = deduped_jobs[:30]

        # Build Entities & Relationships
        entities = []
        relationships = []
        seen_orgs = set()
        seen_locs = set()

        for j in deduped_jobs:
            # Job Entity
            j_id_text = j.source_url or f"{j.company}|{j.title}|{j.location}"
            j_id = _stable_id("job", j_id_text)
            ev = j.evidence[0] if j.evidence else None
            ev_list = [ev] if ev else []

            j_ent = IntelligenceEntity(
                id=j_id,
                type="job",
                label=j.title,
                evidence=ev_list
            )
            entities.append(j_ent)

            # Org Entity
            if j.company:
                org_id = _stable_id("org", j.company)
                if org_id not in seen_orgs:
                    seen_orgs.add(org_id)
                    org_ent = IntelligenceEntity(
                        id=org_id,
                        type="organization",
                        label=j.company,
                        evidence=ev_list
                    )
                    entities.append(org_ent)

                rel_org = IntelligenceRelationship(
                    source=j_id,
                    target=org_id,
                    type="offered_by",
                    confidence="high",
                    evidence=ev_list
                )
                relationships.append(rel_org)

            # Loc Entity
            if j.location:
                loc_id = _stable_id("loc", j.location)
                if loc_id not in seen_locs:
                    seen_locs.add(loc_id)
                    loc_ent = IntelligenceEntity(
                        id=loc_id,
                        type="location",
                        label=j.location,
                        evidence=ev_list
                    )
                    entities.append(loc_ent)

                rel_loc = IntelligenceRelationship(
                    source=j_id,
                    target=loc_id,
                    type="located_in",
                    confidence="high",
                    evidence=ev_list
                )
                relationships.append(rel_loc)

        return deduped_jobs, entities, relationships, status

    finally:
        if close_client:
            await client.aclose()
