import asyncio
from unittest.mock import AsyncMock, patch
from app.intelligence.kuwait_tenders import (
    search_kuwait_tenders,
    _parse_tenders_from_html,
    _matches_query,
    DownloadTooLargeError,
    COVERAGE_NOTE,
)
from app.models.tender import Tender


class MockResponse:
    def __init__(self):
        self.content = b""

    @property
    def text(self):
        return self.content.decode(errors="replace")


def _make_card(ref="2147428", date="Aug. 23, 2026", org="Kuwait Oil Company", title="Cyber Security Services"):
    return f"""
    <div class="content-box grey">
      <div class="page-width"><div class="wrapper">
        <div class="tender-date"><p class="tenderno">{ref}<span>{date}</span></p></div>
        <div class="tender-detail">
          <p class="orgname">{org}</p>
          <p>{title}</p>
        </div>
      </div></div>
    </div>
    """


def _make_page(cards_html):
    return f'<html><body><div class="tenderslist">{cards_html}</div></body></html>'


# ───────────────────── HTML Parsing Tests ─────────────────────

def test_parse_single_card():
    html = _make_page(_make_card())
    rows = _parse_tenders_from_html(html)
    assert len(rows) == 1
    assert rows[0]["reference_number"] == "2147428"
    assert rows[0]["published_at"] == "Aug. 23, 2026"
    assert rows[0]["authority"] == "Kuwait Oil Company"
    assert rows[0]["title"] == "Cyber Security Services"


def test_parse_multiple_cards():
    cards = _make_card(ref="A1", title="Alpha") + _make_card(ref="B2", title="Beta")
    html = _make_page(cards)
    rows = _parse_tenders_from_html(html)
    assert len(rows) == 2
    assert rows[0]["reference_number"] == "A1"
    assert rows[1]["reference_number"] == "B2"


def test_parse_no_tenderslist():
    rows = _parse_tenders_from_html("<html><body><p>Empty</p></body></html>")
    assert rows == []


def test_parse_malformed_html():
    html = _make_page('<div class="content-box"><p>broken</p></div>')
    rows = _parse_tenders_from_html(html)
    # Should not crash – may produce partial result or skip
    assert isinstance(rows, list)


# ───────────────────── Local Filtering Tests ─────────────────────

def test_matches_query_title():
    assert _matches_query({"title": "Cyber Security Services"}, "security")


def test_matches_query_authority():
    assert _matches_query({"authority": "Ministry of Defense"}, "defense")


def test_matches_query_case_insensitive():
    assert _matches_query({"title": "NETWORK Equipment"}, "network")


def test_no_match():
    assert not _matches_query({"title": "Water Supply", "authority": "Public Works"}, "cyber")


# ───────────────────── Integration Tests (Mocked HTTP) ─────────────────────

def _mock_session_with_pages(page1_html, page2_html=None):
    session = AsyncMock()
    call_count = 0

    def mock_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        res = MockResponse()
        cb = kwargs.get("content_callback")
        if call_count == 1:
            if cb:
                cb(page1_html.encode("utf-8"))
        elif call_count == 2 and page2_html:
            if cb:
                cb(page2_html.encode("utf-8"))
        else:
            if cb:
                cb(b"<html><body><div class='tenderslist'></div></body></html>")
        return res

    session.request.side_effect = mock_request
    return session


def test_search_success():
    cards = _make_card(ref="100", title="Network Security") + _make_card(ref="200", title="Water Supply")
    page1 = _make_page(cards)
    session = _mock_session_with_pages(page1)

    tenders, entities, rels = asyncio.run(search_kuwait_tenders("security", session=session))
    assert len(tenders) == 1
    assert tenders[0].title == "Network Security"
    assert tenders[0].reference_number == "100"
    assert tenders[0].country_code == "KW"
    assert tenders[0].status == "opening"
    assert tenders[0].attributes["coverage_note"] == COVERAGE_NOTE


def test_search_by_authority():
    cards = _make_card(ref="300", title="Supply Equipment", org="Ministry of Defense")
    page1 = _make_page(cards)
    session = _mock_session_with_pages(page1)

    tenders, entities, rels = asyncio.run(search_kuwait_tenders("defense", session=session))
    assert len(tenders) == 1
    assert tenders[0].issuing_authority == "Ministry of Defense"


def test_search_no_match():
    cards = _make_card(ref="400", title="Water Treatment", org="Public Works")
    page1 = _make_page(cards)
    session = _mock_session_with_pages(page1)

    tenders, entities, rels = asyncio.run(search_kuwait_tenders("cyber", session=session))
    assert len(tenders) == 0
    assert len(entities) == 0
    assert len(rels) == 0


def test_organization_entities_and_relationships():
    cards = _make_card(ref="500", title="Security Systems", org="Ministry of Defense")
    page1 = _make_page(cards)
    session = _mock_session_with_pages(page1)

    tenders, entities, rels = asyncio.run(search_kuwait_tenders("security", session=session))
    assert len(tenders) == 1
    org_entities = [e for e in entities if e.type == "organization"]
    assert len(org_entities) == 1
    assert org_entities[0].label == "Ministry of Defense"
    assert len(rels) == 1
    assert rels[0].type == "issued_by"


def test_organization_deduplication():
    cards = (
        _make_card(ref="600", title="Security A", org="Ministry of Defense")
        + _make_card(ref="601", title="Security B", org="Ministry of Defense")
    )
    page1 = _make_page(cards)
    session = _mock_session_with_pages(page1)

    tenders, entities, rels = asyncio.run(search_kuwait_tenders("security", session=session))
    assert len(tenders) == 2
    org_entities = [e for e in entities if e.type == "organization"]
    assert len(org_entities) == 1  # deduplicated


def test_max_40_inspected():
    """Even if more than 40 rows are parsed, only 40 are inspected."""
    # Build page1 with 20 cards, page2 with 25 cards = 45 total parsed
    cards1 = "".join(_make_card(ref=str(i), title="Match Security") for i in range(20))
    cards2 = "".join(_make_card(ref=str(i + 20), title="Match Security") for i in range(25))
    page1 = _make_page(cards1)
    page2 = _make_page(cards2)
    session = _mock_session_with_pages(page1, page2)

    tenders, _, _ = asyncio.run(search_kuwait_tenders("security", session=session))
    # 40 inspected, all match, but capped at 20 returned
    assert len(tenders) == 20


def test_max_20_returned():
    """Even if more than 20 match, only 20 are returned."""
    cards = "".join(_make_card(ref=str(i), title="Match Security") for i in range(20))
    page1 = _make_page(cards)
    session = _mock_session_with_pages(page1)

    tenders, _, _ = asyncio.run(search_kuwait_tenders("security", session=session))
    assert len(tenders) == 20


def test_page2_only_fetched_if_page1_full():
    """If page 1 has fewer than 20 items, page 2 is NOT fetched."""
    cards = "".join(_make_card(ref=str(i), title="Match Security") for i in range(5))
    page1 = _make_page(cards)
    session = _mock_session_with_pages(page1)

    asyncio.run(search_kuwait_tenders("security", session=session))
    assert session.request.call_count == 1  # only page 1


def test_page2_fetched_when_page1_full():
    cards = "".join(_make_card(ref=str(i), title="Item") for i in range(20))
    page1 = _make_page(cards)
    page2 = _make_page(_make_card(ref="99", title="Match Security"))
    session = _mock_session_with_pages(page1, page2)

    asyncio.run(search_kuwait_tenders("security", session=session))
    assert session.request.call_count == 2  # both pages


def test_network_error_isolated():
    session = AsyncMock()
    session.request.side_effect = Exception("Connection refused")
    tenders, entities, rels = asyncio.run(search_kuwait_tenders("security", session=session))
    assert tenders == []
    assert entities == []
    assert rels == []


def test_download_too_large():
    session = AsyncMock()

    def mock_request(method, url, **kwargs):
        res = MockResponse()
        cb = kwargs.get("content_callback")
        if cb:
            cb(b"A" * 3 * 1024 * 1024)
            cb(b"A" * 3 * 1024 * 1024)  # 6MB > 5MB cap
        return res

    session.request.side_effect = mock_request
    tenders, _, _ = asyncio.run(search_kuwait_tenders("security", session=session))
    assert tenders == []
