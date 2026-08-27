import asyncio
import hashlib
from typing import List, Tuple, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

from app.models.document import Document, DocumentSearchRequest
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship, Evidence

def _stable_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

class SourceConfig:
    def __init__(self, organization: str, aliases: List[str], country_code: str, index_url: str, allowed_hosts: List[str], category_mapping: Dict[str, str]):
        self.organization = organization
        self.aliases = [a.lower() for a in aliases]
        self.country_code = country_code.upper()
        self.index_url = index_url
        self.allowed_hosts = [h.lower() for h in allowed_hosts]
        self.category_mapping = category_mapping

CORPORATE_SOURCES = [
    SourceConfig(
        organization="SABIC",
        aliases=["sabic"],
        country_code="SA",
        index_url="https://www.sabic.com/en/investors",
        allowed_hosts=["www.sabic.com", "sabic.com"],
        category_mapping={
            "annual report": "Annual Report",
            "board of directors": "Board Report",
            "investor day": "Investor Presentation",
            "sustainability": "ESG Report",
            "esg": "ESG Report"
        }
    )
]

async def _process_source(source: SourceConfig, request: DocumentSearchRequest) -> Tuple[List[Document], List[IntelligenceEntity], List[IntelligenceRelationship]]:
    documents = []
    entities = []
    relationships = []

    client = httpx.AsyncClient(verify=True, timeout=8.0)
    current_url = source.index_url
    redirects = 0
    content = b""
    
    while redirects <= 2:
        parsed_current = urlparse(current_url)
        if parsed_current.scheme != "https" or parsed_current.hostname.lower() not in source.allowed_hosts:
            return [], [], []

        async with client.stream("GET", current_url) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    break
                current_url = urljoin(current_url, location)
                redirects += 1
                continue
            
            if response.status_code != 200:
                return [], [], []

            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                return [], [], []

            async for chunk in response.aiter_bytes():
                content += chunk
                if len(content) > 5 * 1024 * 1024:
                    return [], [], []
            
            break
    else:
        return [], [], []

    await client.aclose()

    if not content:
        return [], [], []

    soup = BeautifulSoup(content, 'html.parser')
    seen_urls = set()
    
    q_lower = request.query.lower()
    req_type_lower = request.document_type.lower() if request.document_type else None

    org_id = f"org_{_stable_id(source.organization)}"
    org_entity = IntelligenceEntity(id=org_id, type="organization", label=source.organization, attributes={})
    org_added = False

    for a in soup.find_all('a', href=True):
        href = a.get("href", "").strip()
        if not href.lower().endswith(".pdf") and ".pdf" not in href.lower():
            continue

        full_url = urljoin(current_url, href)
        parsed_url = urlparse(full_url)

        if parsed_url.scheme != "https" or parsed_url.hostname.lower() not in source.allowed_hosts:
            continue

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        title = " ".join(a.text.strip().replace("\n", " ").split())
        if not title:
            title = parsed_url.path.split("/")[-1]

        doc_type = None
        title_lower = title.lower()
        for k, v in source.category_mapping.items():
            if k in title_lower:
                doc_type = v
                break

        if q_lower not in title_lower and (not doc_type or q_lower not in doc_type.lower()) and q_lower not in source.organization.lower():
            continue

        if req_type_lower:
            if not doc_type or req_type_lower not in doc_type.lower():
                continue

        doc_id_str = _stable_id(full_url)
        doc_id = f"doc_{doc_id_str}"
        
        doc = Document(
            id=doc_id,
            title=title,
            document_type=doc_type,
            organization=source.organization,
            country_code=source.country_code,
            source_url=current_url,
            file_url=full_url,
            mime_type="application/pdf",
            evidence=[Evidence(source="corporate_ir", source_url=current_url)],
            attributes={}
        )
        
        doc_entity = IntelligenceEntity(id=doc_id, type="document", label=title, attributes={"document_type": doc_type, "file_url": full_url})
        rel = IntelligenceRelationship(source=doc_id, target=org_id, type="published_by", confidence="high")

        documents.append(doc)
        entities.append(doc_entity)
        relationships.append(rel)
        
        if not org_added:
            entities.append(org_entity)
            org_added = True

        if len(documents) >= 30:
            break

    return documents, entities, relationships

async def search_corporate_ir_documents(request: DocumentSearchRequest) -> Tuple[List[Document], List[IntelligenceEntity], List[IntelligenceRelationship]]:
    req_country = request.country_code.upper()
    req_org = request.organization.lower() if request.organization else None

    tasks = []
    for src in CORPORATE_SOURCES:
        if src.country_code != req_country:
            continue
        if req_org and req_org != src.organization.lower() and req_org not in src.aliases:
            continue
        tasks.append(_process_source(src, request))

    if not tasks:
        return [], [], []

    results = await asyncio.gather(*tasks)
    
    all_docs = []
    all_ents = []
    all_rels = []
    seen_ents = set()
    
    for res in results:
        docs, ents, rels = res
        all_docs.extend(docs)
        for e in ents:
            if e.id not in seen_ents:
                seen_ents.add(e.id)
                all_ents.append(e)
        all_rels.extend(rels)

    all_docs = all_docs[:30]
    
    doc_ids = {d.id for d in all_docs}
    pruned_rels = [r for r in all_rels if r.source in doc_ids]
    pruned_ents = [e for e in all_ents if e.type == "organization" or e.id in doc_ids]

    return all_docs, pruned_ents, pruned_rels
