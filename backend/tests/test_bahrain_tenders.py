import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager
import json

from app.intelligence.bahrain_tenders import (
    _parse_tenders_from_html,
    _build_payload,
    search_bahrain_tenders,
    DownloadTooLargeError
)


# --- HTML Parsing Tests ---

def _make_row(title="Telecom Security Drill", ref="TRA/2025/005", org="TRA", pub="29, Aug,2025", dead="24 Sep,2025", purchase="10 Sep,2025", ttype="Public", link="/TenderDetails/?id=123"):
    return f"""
    <div class="rows">
        <div class="column" data-label="No./Tender Subject">
            <a href="{link}"><span>{ref}</span>{title}</a>
        </div>
        <div class="column" data-label="Tender Type">{ttype}</div>
        <div class="column" data-label="Purchasing Authority">{org}</div>
        <div class="column" data-label="Publish Date">{pub}</div>
        <div class="column" data-label="Purchase Before">{purchase}</div>
        <div class="column" data-label="Closing Date">{dead}</div>
        <a href="{link}">Details</a>
    </div>
    """

def test_parse_single_row():
    html = _make_row()
    rows = _parse_tenders_from_html(html)
    assert len(rows) == 1
    assert rows[0]["reference_number"] == "TRA/2025/005"
    assert rows[0]["title_raw"] == "Telecom Security Drill"
    assert rows[0]["authority"] == "TRA"
    assert rows[0]["published_at"] == "29, Aug,2025"
    assert rows[0]["deadline"] == "24 Sep,2025"
    assert rows[0]["purchase_before"] == "10 Sep,2025"
    assert rows[0]["tender_type"] == "Public"
    assert rows[0]["source_url"] == "https://www.tenderboard.gov.bh/TenderDetails/?id=123"

def test_parse_absolute_link():
    html = _make_row(link="https://other.gov.bh/link")
    rows = _parse_tenders_from_html(html)
    assert rows[0]["source_url"] == "https://other.gov.bh/link"

def test_parse_empty():
    rows = _parse_tenders_from_html("<div>Empty</div>")
    assert rows == []

def test_parse_malformed():
    html = "<div class='rows'><div class='column' data-label='No./Tender Subject'>Broken</div></div>"
    rows = _parse_tenders_from_html(html)
    assert len(rows) == 1
    assert rows[0]["title_raw"] == "Broken"


# --- HTTP Mocking ---

class MockResponse:
    def __init__(self, json_data=None, chunks=None):
        self._json = json_data
        self._chunks = chunks
        
    def raise_for_status(self):
        pass
        
    async def aiter_bytes(self):
        if self._chunks:
            for c in self._chunks:
                yield c
        elif self._json is not None:
            yield json.dumps(self._json).encode("utf-8")
        else:
            yield b"{}"

class MockClient:
    def __init__(self, page1_html=None, page2_html=None, chunks=None, error=None):
        self.call_count = 0
        self.page1_html = page1_html
        self.page2_html = page2_html
        self.chunks = chunks
        self.error = error
        
    @asynccontextmanager
    async def stream(self, method, url, **kwargs):
        if self.error:
            raise self.error
            
        self.call_count += 1
        
        if self.chunks:
            yield MockResponse(chunks=self.chunks)
            return
            
        if self.call_count == 1 and self.page1_html is not None:
            yield MockResponse({"d": self.page1_html})
        elif self.call_count == 2 and self.page2_html is not None:
            yield MockResponse({"d": self.page2_html})
        else:
            yield MockResponse({"d": ""})


# --- Integration Tests (Mocked HTTP) ---

def test_search_success():
    page1 = _make_row(title="Cyber Security Drill") + _make_row(title="Network Support")
    client = MockClient(page1_html=page1)

    tenders, entities, rels = asyncio.run(search_bahrain_tenders("security", client=client))
    
    assert len(tenders) == 2
    assert "Cyber Security Drill" in tenders[0].title
    assert tenders[0].reference_number == "TRA/2025/005"
    assert tenders[0].country_code == "BH"
    assert tenders[0].status is None  # explicitly unset
    assert tenders[0].issuing_authority == "TRA"
    assert tenders[0].attributes["purchase_before"] == "10 Sep,2025"
    assert tenders[0].attributes["tender_type"] == "Public"

def test_organization_entities_and_relationships():
    page1 = _make_row(org="Bahrain Bourse")
    client = MockClient(page1_html=page1)

    tenders, entities, rels = asyncio.run(search_bahrain_tenders("security", client=client))
    assert len(tenders) == 1
    org_entities = [e for e in entities if e.type == "organization"]
    assert len(org_entities) == 1
    assert org_entities[0].label == "Bahrain Bourse"
    assert len(rels) == 1
    assert rels[0].type == "issued_by"

def test_organization_deduplication():
    page1 = _make_row(org="TRA") + _make_row(title="Another", org="TRA")
    client = MockClient(page1_html=page1)

    tenders, entities, rels = asyncio.run(search_bahrain_tenders("security", client=client))
    assert len(tenders) == 2
    org_entities = [e for e in entities if e.type == "organization"]
    assert len(org_entities) == 1

def test_page2_fetched_if_page1_has_10():
    page1 = "".join([_make_row(title=f"Item {i}") for i in range(10)])
    page2 = _make_row(title="Item 11")
    client = MockClient(page1_html=page1, page2_html=page2)

    tenders, _, _ = asyncio.run(search_bahrain_tenders("security", client=client))
    assert client.call_count == 2
    assert len(tenders) == 11

def test_page2_not_fetched_if_page1_under_10():
    page1 = "".join([_make_row(title=f"Item {i}") for i in range(9)])
    client = MockClient(page1_html=page1)

    tenders, _, _ = asyncio.run(search_bahrain_tenders("security", client=client))
    assert client.call_count == 1
    assert len(tenders) == 9

def test_max_20_returned():
    page1 = "".join([_make_row(title=f"Item {i}") for i in range(10)])
    page2 = "".join([_make_row(title=f"Item {i+10}") for i in range(15)]) # 25 total
    client = MockClient(page1_html=page1, page2_html=page2)

    tenders, _, _ = asyncio.run(search_bahrain_tenders("security", client=client))
    assert client.call_count == 2
    assert len(tenders) == 20

def test_network_error_isolated():
    client = MockClient(error=Exception("Connection refused"))
    tenders, entities, rels = asyncio.run(search_bahrain_tenders("security", client=client))
    assert tenders == []
    assert entities == []
    assert rels == []

def test_malformed_json_isolated():
    client = MockClient(chunks=[b"{bad json}"])
    tenders, _, _ = asyncio.run(search_bahrain_tenders("security", client=client))
    assert tenders == []

def test_download_too_large():
    # 6MB payload in chunks
    chunks = [b"A" * 3 * 1024 * 1024, b"A" * 3 * 1024 * 1024]
    client = MockClient(chunks=chunks)
    
    tenders, _, _ = asyncio.run(search_bahrain_tenders("security", client=client))
    assert tenders == []
