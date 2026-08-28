import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.intelligence.qatar_tenders import search_qatar_tenders, DownloadTooLargeError
from app.models.tender import Tender

class MockResponse:
    def __init__(self):
        self.content = b""

    @property
    def text(self):
        return self.content.decode(errors="replace")

@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session

def test_qatar_tenders_missing_token(mock_session):
    def mock_request(method, url, **kwargs):
        res = MockResponse()
        cb = kwargs.get("content_callback")
        if cb: cb(b"<html><body>No token here</body></html>")
        return res
    mock_session.request.side_effect = mock_request
    
    tenders, entities, relations = asyncio.run(search_qatar_tenders("cyber", session=mock_session))
    assert not tenders
    assert not entities
    assert not relations

def test_qatar_tenders_success(mock_session):
    def mock_request(method, url, **kwargs):
        res = MockResponse()
        cb = kwargs.get("content_callback")
        if method == "GET":
            if cb: cb(b'<html><body><input name="__RequestVerificationToken" value="abc123" /></body></html>')
        else:
            html = """
            <html><body>
                <div class="row">
                    <a href="/TendersOnlineServices/TenderDetails/111">Network Tech</a>
                    1234/2026 Publish date 27/08/2026
                </div>
                <div class="row">
                    <a href="/TendersOnlineServices/TenderDetails/222">Cyber Tech</a>
                    4321/2026 Publish date 28/08/2026
                </div>
            </body></html>
            """
            if cb: cb(html.encode())
        return res
    mock_session.request.side_effect = mock_request
    
    tenders, entities, relations = asyncio.run(search_qatar_tenders("cyber", session=mock_session))
    assert len(tenders) == 2
    
    assert mock_session.request.call_args[1]["data"]["__RequestVerificationToken"] == "abc123"
    assert mock_session.request.call_args[1]["data"]["SearchData.TenderSubject"] == "cyber"
    
    assert tenders[0].title == "Network Tech"
    assert tenders[0].reference_number == "1234/2026"
    assert tenders[0].deadline == "27/08/2026"
    assert tenders[0].country_code == "QA"
    assert "Network Tech" in entities[0].label

def test_qatar_tenders_max_20_and_dedup(mock_session):
    def mock_request(method, url, **kwargs):
        res = MockResponse()
        cb = kwargs.get("content_callback")
        if method == "GET":
            if cb: cb(b'<html><body><input name="__RequestVerificationToken" value="abc" /></body></html>')
        else:
            html = "<html><body>"
            for i in range(25):
                html += f'<div class="row"><a href="/TendersOnlineServices/TenderDetails/{i}">Tender {i}</a></div>'
            html += '<div class="row"><a href="/TendersOnlineServices/TenderDetails/5">Tender 5 (Duplicate)</a></div>'
            html += "</body></html>"
            if cb: cb(html.encode())
        return res
    mock_session.request.side_effect = mock_request
    
    tenders, entities, relations = asyncio.run(search_qatar_tenders("cyber", session=mock_session))
    assert len(tenders) == 20 # Max 20

def test_qatar_tenders_network_error(mock_session):
    mock_session.request.side_effect = Exception("Network timeout")
    tenders, entities, relations = asyncio.run(search_qatar_tenders("cyber", session=mock_session))
    assert not tenders

def test_qatar_tenders_too_large(mock_session):
    def mock_request(method, url, **kwargs):
        res = MockResponse()
        cb = kwargs.get("content_callback")
        if cb: 
            # Simulate chunks until it throws
            cb(b"A" * 3 * 1024 * 1024) # 3MB chunk
            cb(b"A" * 3 * 1024 * 1024) # 3MB chunk -> total 6MB > 5MB limit
        return res
    mock_session.request.side_effect = mock_request
    tenders, entities, relations = asyncio.run(search_qatar_tenders("cyber", session=mock_session))
    assert not tenders
