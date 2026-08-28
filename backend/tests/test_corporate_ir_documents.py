import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.document import DocumentSearchRequest
from app.intelligence.corporate_ir_documents import search_corporate_ir_documents, CORPORATE_SOURCES, SourceConfig, _stable_id

class MockStreamResponse:
    def __init__(self, status_code, content, headers=None):
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html"}
        self.content = content

    async def aiter_bytes(self):
        yield self.content

class MockStreamContextManager:
    def __init__(self, responses):
        self.responses = responses
        self.index = 0

    async def __aenter__(self):
        resp = self.responses[self.index]
        self.index += 1
        return resp

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def mock_httpx_client():
    with patch("app.intelligence.corporate_ir_documents.httpx.AsyncClient") as mock_client_class:
        mock_instance = AsyncMock()
        mock_instance.stream = MagicMock()
        mock_client_class.return_value = mock_instance
        yield mock_client_class, mock_instance

def test_search_corporate_ir_documents_valid(mock_httpx_client):
    mock_client_class, mock_instance = mock_httpx_client
    async def run_test():
        html = b"""
        <html>
            <body>
                <a href="/en/Images/SABIC-Annual-Report-2023.pdf">Annual Report 2023</a>
                <a href="https://www.sabic.com/en/Images/SABIC-Board.pdf">Board of Directors 2023</a>
                <a href="/en/Images/SABIC-ESG.pdf">Sustainability Report 2023</a>
                <a href="/en/Images/SABIC-Investor.pdf">Investor day 2023</a>
                <a href="/en/Images/unknown.pdf">Some Random Document</a>
                <a href="http://www.google.com/test.pdf">Off Domain</a>
                <a href="/en/Images/not-a-pdf.html">Not a PDF</a>
            </body>
        </html>
        """
        mock_instance.stream.return_value = MockStreamContextManager([MockStreamResponse(200, html)])

        req = DocumentSearchRequest(query="SABIC", country_code="SA")
        docs, ents, rels = await search_corporate_ir_documents(req)

        assert len(docs) == 5
        assert docs[0].title == "Annual Report 2023"
        assert docs[0].document_type == "Annual Report"
        assert docs[1].document_type == "Board Report"
        assert docs[2].document_type == "ESG Report"
        assert docs[3].document_type == "Investor Presentation"
        assert docs[4].document_type is None

        assert docs[0].organization == "SABIC"
        assert docs[0].source_url == "https://www.sabic.com/en/investors"
        assert docs[0].file_url == "https://www.sabic.com/en/Images/SABIC-Annual-Report-2023.pdf"

        file_urls = [d.file_url for d in docs]
        assert "http://www.google.com/test.pdf" not in file_urls
        assert "https://www.sabic.com/en/Images/not-a-pdf.html" not in file_urls

        assert len(ents) == 6
        assert len(rels) == 5

        # Regression check for headers
        mock_client_class.assert_called_once()
        kwargs = mock_client_class.call_args.kwargs
        assert "headers" in kwargs
        assert "User-Agent" in kwargs["headers"]
        assert "Accept" in kwargs["headers"]
        assert "Mozilla" in kwargs["headers"]["User-Agent"]

    asyncio.run(run_test())

def test_search_corporate_ir_documents_filtering(mock_httpx_client):
    mock_client_class, mock_instance = mock_httpx_client
    async def run_test():
        html = b"""
        <html>
            <body>
                <a href="/en/Images/SABIC-Annual-Report-2023.pdf">Annual Report 2023</a>
                <a href="https://www.sabic.com/en/Images/SABIC-Board.pdf">Board of Directors 2023</a>
            </body>
        </html>
        """
        mock_instance.stream.return_value = MockStreamContextManager([MockStreamResponse(200, html)])

        req = DocumentSearchRequest(query="2023", country_code="SA", document_type="Annual Report")
        docs, ents, rels = await search_corporate_ir_documents(req)
        assert len(docs) == 1
        assert docs[0].document_type == "Annual Report"
    asyncio.run(run_test())

def test_search_corporate_ir_documents_redirect(mock_httpx_client):
    mock_client_class, mock_instance = mock_httpx_client
    async def run_test():
        redirect = MockStreamResponse(301, b"", {"location": "/new-investors"})
        final = MockStreamResponse(200, b"<html><a href='test.pdf'>SABIC Doc</a></html>")

        mock_instance.stream.return_value = MockStreamContextManager([redirect, final])

        req = DocumentSearchRequest(query="SABIC", country_code="SA")
        docs, ents, rels = await search_corporate_ir_documents(req)

        assert len(docs) == 1
        assert docs[0].source_url == "https://www.sabic.com/new-investors"
        assert docs[0].file_url == "https://www.sabic.com/test.pdf"
    asyncio.run(run_test())

def test_search_corporate_ir_documents_unsupported():
    async def run_test():
        req = DocumentSearchRequest(query="SABIC", country_code="US")
        docs, ents, rels = await search_corporate_ir_documents(req)
        assert len(docs) == 0

        req = DocumentSearchRequest(query="SABIC", country_code="SA", organization="Aramco")
        docs, ents, rels = await search_corporate_ir_documents(req)
        assert len(docs) == 0
    asyncio.run(run_test())

def test_search_corporate_ir_documents_size_limit(mock_httpx_client):
    mock_client_class, mock_instance = mock_httpx_client
    async def run_test():
        content = b"a" * (5 * 1024 * 1024 + 100)
        mock_instance.stream.return_value = MockStreamContextManager([MockStreamResponse(200, content)])

        req = DocumentSearchRequest(query="SABIC", country_code="SA")
        docs, ents, rels = await search_corporate_ir_documents(req)
        assert len(docs) == 0
    asyncio.run(run_test())

def test_deterministic_id():
    id1 = _stable_id("https://example.com/test.pdf")
    id2 = _stable_id("https://example.com/test.pdf")
    id3 = _stable_id("https://example.com/other.pdf")

    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 16
