import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager

from app.intelligence.successfactors_jobs import (
    _parse_sf_jobs_html,
    _match_sources,
    search_successfactors_jobs,
    DownloadTooLargeError
)
from app.models.job import Job

# --- HTML Parsing Tests ---

def _make_row(title="Engineer", link="/job/123", loc="SA", dept="IT", fac="100", date="Aug 1, 2026"):
    return f"""
    <div class="search-page">
    <tr class="data-row">
        <td><a class="jobTitle-link" href="{link}">{title}</a></td>
        <td><span class="jobLocation">{loc}</span></td>
        <td><span class="jobDepartment">{dept}</span></td>
        <td><span class="jobFacility">{fac}</span></td>
        <td><span class="jobDate">{date}</span></td>
    </tr>
    </div>
    """

def test_parse_sf_row():
    html = _make_row()
    rows = _parse_sf_jobs_html(html, "https://careers.test.com")
    assert len(rows) == 1
    assert rows[0]["title"] == "Engineer"
    assert rows[0]["source_url"] == "https://careers.test.com/job/123"
    assert rows[0]["location"] == "SA"
    assert rows[0]["department"] == "IT"
    assert rows[0]["facility"] == "100"
    assert rows[0]["published_at"] == "Aug 1, 2026"

def test_parse_missing_fields():
    html = """<div class="search-page"><tr class="data-row">
        <td><span class="jobTitle">Fallback Title</span></td>
    </tr></div>"""
    rows = _parse_sf_jobs_html(html, "https://careers.test.com")
    assert len(rows) == 1
    assert rows[0]["title"] == "Fallback Title"
    assert "source_url" not in rows[0]
    assert "location" not in rows[0]

def test_max_25_rows_parsed():
    html = "".join([_make_row(title=f"Job {i}") for i in range(30)])
    rows = _parse_sf_jobs_html(html, "https://careers.test.com")
    assert len(rows) == 25

# --- Source Matching ---

def test_match_sources_no_company():
    sources = _match_sources("SA", None)
    assert len(sources) == 3
    names = [s[0] for s in sources]
    assert "Saudi Aramco" in names
    assert "STC" in names
    assert "SABIC" in names

def test_match_sources_by_company():
    sources = _match_sources("SA", " STC ")
    assert len(sources) == 1
    assert sources[0][0] == "STC"

def test_match_sources_alias():
    sources = _match_sources("SA", "saudi telecom")
    assert len(sources) == 1
    assert sources[0][0] == "STC"

def test_match_sources_unsupported():
    sources = _match_sources("SA", "Unknown Co")
    assert len(sources) == 0

def test_match_sources_unsupported_country():
    sources = _match_sources("AE", None)
    assert len(sources) == 0

# --- HTTP Mocking ---

class MockResponse:
    def __init__(self, text=None, chunks=None):
        self._text = text
        self._chunks = chunks

    def raise_for_status(self):
        pass

    async def aiter_bytes(self):
        if self._chunks:
            for c in self._chunks:
                yield c
        elif self._text is not None:
            yield self._text.encode("utf-8")
        else:
            yield b""

class MockClient:
    def __init__(self, text_map=None, chunks_map=None, error_map=None):
        self.text_map = text_map or {}
        self.chunks_map = chunks_map or {}
        self.error_map = error_map or {}
        self.call_count = 0

    @asynccontextmanager
    async def stream(self, method, url, **kwargs):
        self.call_count += 1

        # Exact match or substring
        err = next((v for k,v in self.error_map.items() if k in url), None)
        if err:
            raise err

        chunks = next((v for k,v in self.chunks_map.items() if k in url), None)
        if chunks:
            yield MockResponse(chunks=chunks)
            return

        text = next((v for k,v in self.text_map.items() if k in url), "")
        yield MockResponse(text=text)

# --- Integration Tests ---

def test_search_all_sa():
    aramco = _make_row(title="Aramco Job", link="/a")
    stc = _make_row(title="STC Job", link="/s")
    sabic = _make_row(title="SABIC Job", link="/b")

    client = MockClient(text_map={
        "aramco.com": aramco,
        "stc.com.sa": stc,
        "sabic.com": sabic
    })

    jobs, ents, rels, status = asyncio.run(search_successfactors_jobs("engineer", "SA", None, client=client))

    assert len(jobs) == 3
    assert client.call_count == 3
    titles = [j.title for j in jobs]
    assert "Aramco Job" in titles
    assert "STC Job" in titles
    assert "SABIC Job" in titles

    orgs = [e for e in ents if e.type == "organization"]
    assert len(orgs) == 3
    locs = [e for e in ents if e.type == "location"]
    assert len(locs) == 1  # Deduped "SA"

def test_search_specific_company():
    stc = _make_row(title="STC Job")
    client = MockClient(text_map={"stc.com.sa": stc})

    jobs, _, _, _ = asyncio.run(search_successfactors_jobs("engineer", "SA", "stc", client=client))
    assert len(jobs) == 1
    assert client.call_count == 1
    assert jobs[0].company == "STC"

def test_failure_isolation():
    aramco = _make_row(title="Aramco Job")
    client = MockClient(
        text_map={"aramco.com": aramco},
        error_map={"stc.com.sa": Exception("Network Error")}
    )

    jobs, _, _, _ = asyncio.run(search_successfactors_jobs("engineer", "SA", None, client=client))
    assert len(jobs) == 1  # STC failed, but Aramco succeeded
    assert jobs[0].company == "Saudi Aramco"

def test_oversized_response_isolation():
    aramco = _make_row(title="Aramco Job")
    client = MockClient(
        text_map={"aramco.com": aramco},
        chunks_map={"stc.com.sa": [b"A" * 3 * 1024 * 1024, b"A" * 3 * 1024 * 1024]}
    )

    jobs, _, _, _ = asyncio.run(search_successfactors_jobs("engineer", "SA", None, client=client))
    assert len(jobs) == 1
    assert jobs[0].company == "Saudi Aramco"

def test_deduplication():
    # Identical URL across two companies (unlikely, but tests dedup)
    r1 = _make_row(title="Job A", link="https://careers.example.com/same")
    client = MockClient(text_map={"aramco.com": r1, "stc.com.sa": r1})

    jobs, _, _, _ = asyncio.run(search_successfactors_jobs("engineer", "SA", None, client=client))
    assert len(jobs) == 1

def test_max_30_limit():
    html = "".join([_make_row(title=f"Job {i}", link=f"/j{i}") for i in range(25)])
    client = MockClient(text_map={
        "aramco.com": html,
        "stc.com.sa": html
    })

    jobs, _, _, _ = asyncio.run(search_successfactors_jobs("engineer", "SA", None, client=client))
    # 25 from Aramco + 25 from STC = 50 -> capped at 30
    assert len(jobs) == 30

def test_deterministic_ids():
    from app.intelligence.successfactors_jobs import _stable_id
    # We test that production _stable_id logic produces exactly the same ID

    id1 = _stable_id('job', 'https://example.com/job/1')
    id2 = _stable_id('job', 'https://example.com/job/1')
    assert id1 == id2
    assert id1 == 'job_28946e28a2ca608e'

    id3 = _stable_id('org', 'Saudi Aramco')
    id4 = _stable_id('org', 'Saudi Aramco')
    assert id3 == id4
    assert id3 == 'org_06e94283fa724fd9'




def test_search_oq_oman():
    oq_html = _make_row(title="OQ Process Engineer", link="/job/oq-123", loc="Muscat, OM", dept="Refinery")
    client = MockClient(text_map={"careers.oq.com": oq_html})

    jobs, ents, rels, status = asyncio.run(search_successfactors_jobs("engineer", "OM", "OQ", client=client))

    assert status == "collected"
    assert len(jobs) == 1
    assert client.call_count == 1

    j = jobs[0]
    assert j.company == "OQ"
    assert j.title == "OQ Process Engineer"
    assert j.location == "Muscat, OM"
    assert j.department == "Refinery"
    assert j.source_url == "https://careers.oq.com/job/oq-123"

def test_search_oq_alias():
    oq_html = _make_row(title="OQ Job")
    client = MockClient(text_map={"careers.oq.com": oq_html})

    jobs, _, _, _ = asyncio.run(search_successfactors_jobs("engineer", "OM", "oq energy", client=client))
    assert len(jobs) == 1
    assert jobs[0].company == "OQ"

def test_search_oq_does_not_affect_saudi():
    sources = _match_sources("SA", None)
    names = [s[0] for s in sources]
    assert "OQ" not in names

def test_search_oq_failure_semantics():
    client = MockClient(error_map={"careers.oq.com": Exception("Timeout")})
    jobs, _, _, status = asyncio.run(search_successfactors_jobs("engineer", "OM", "OQ", client=client))
    assert status == "error"
    assert len(jobs) == 0
