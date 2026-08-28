import asyncio
import logging
from typing import Tuple

from app.models.intelligence_profile import (
    UnifiedProfileRequest,
    UnifiedProfileResponse,
    UnifiedProfileModules,
    ModuleStatus
)
from app.models.company import CompanyInvestigateRequest, CompanyInvestigateResponse
from app.models.job import JobSearchRequest, JobSearchResponse
from app.models.document import DocumentSearchRequest, DocumentSearchResponse
from app.models.tender import TenderSearchRequest, TenderSearchResponse

from app.api.company import investigate_company
from app.api.jobs import search_jobs
from app.api.documents import search_documents
from app.api.tender import search_tenders
from app.intelligence.correlation import correlate_intelligence
from app.intelligence.infrastructure import investigate_infrastructure
from app.models.intelligence import IntelligenceRelationship
from app.models.infrastructure import InfrastructureInvestigateRequest

logger = logging.getLogger(__name__)

async def build_unified_profile(request: UnifiedProfileRequest) -> UnifiedProfileResponse:
    # Initialize basic response structure
    response = UnifiedProfileResponse(
        status="completed",
        company_name=request.company_name,
        country_code=request.country_code,
        query=request.query,
        modules=UnifiedProfileModules(
            company=ModuleStatus(status="skipped"),
            news=ModuleStatus(status="skipped"),
            jobs=ModuleStatus(status="skipped"),
            documents=ModuleStatus(status="skipped"),
            tenders=ModuleStatus(status="skipped"),
            infrastructure=ModuleStatus(status="skipped")
        )
    )

    all_entities = []
    all_rels = []
    has_error = False

    # 1. Company Intelligence (Always runs, handles News internally)
    try:
        comp_req = CompanyInvestigateRequest(
            company_name=request.company_name,
            country_code=request.country_code
        )
        comp_res = await investigate_company(comp_req)

        response.company = comp_res.company
        response.modules.company = ModuleStatus(status="collected", count=1)

        # Extract News stats
        news_count = sum(1 for e in comp_res.entities if e.type == "news_article")
        if news_count > 0:
            response.modules.news = ModuleStatus(status="collected", count=news_count)
        else:
            # If no news but company succeeded, could be foundation/unavailable. Let's just say foundation or collected 0.
            # We'll use foundation when empty.
            response.modules.news = ModuleStatus(status="foundation", count=0)

        all_entities.extend(comp_res.entities)
        all_rels.extend(comp_res.relationships)

    except Exception as e:
        logger.exception("Company Intelligence failed in unified profile")
        has_error = True
        response.modules.company = ModuleStatus(status="error", error="Company Intelligence failed")
        response.modules.news = ModuleStatus(status="error", error="Skipped due to Company failure")

    # Concurrently launch applicable modules
    infra_task = None
    if response.company and response.company.website:
        try:
            req_infra = InfrastructureInvestigateRequest(domain=response.company.website)
            if req_infra.domain:
                infra_task = asyncio.create_task(investigate_infrastructure(req_infra.domain))
        except Exception:
            pass

    job_task = None
    doc_task = None
    tender_task = None

    if request.query:
        job_req = JobSearchRequest(
            query=request.query,
            country_code=request.country_code,
            company=request.company_name
        )
        job_task = asyncio.create_task(search_jobs(job_req))

        doc_req = DocumentSearchRequest(
            query=request.query,
            country_code=request.country_code,
            organization=request.company_name
        )
        doc_task = asyncio.create_task(search_documents(doc_req))

        tender_req = TenderSearchRequest(
            query=request.query,
            country_code=request.country_code
        )
        tender_task = asyncio.create_task(search_tenders(tender_req))

    # Await tasks and process results deterministically: Company/News (already done) -> Jobs -> Documents -> Tenders -> Infrastructure

    if job_task:
        try:
            job_res = await job_task
            response.jobs = job_res.jobs
            response.modules.jobs = ModuleStatus(status=job_res.status, count=len(job_res.jobs))
            all_entities.extend(job_res.entities)
            all_rels.extend(job_res.relationships)
        except Exception as e:
            logger.exception("Job Intelligence failed in unified profile")
            has_error = True
            response.modules.jobs = ModuleStatus(status="error", error="Job Intelligence failed")

    if doc_task:
        try:
            doc_res = await doc_task
            response.documents = doc_res.documents
            response.modules.documents = ModuleStatus(status=doc_res.status, count=len(doc_res.documents))
            all_entities.extend(doc_res.entities)
            all_rels.extend(doc_res.relationships)
        except Exception as e:
            logger.exception("Document Intelligence failed in unified profile")
            has_error = True
            response.modules.documents = ModuleStatus(status="error", error="Document Intelligence failed")

    if tender_task:
        try:
            tender_res = await tender_task
            response.tenders = tender_res.tenders
            response.modules.tenders = ModuleStatus(status=tender_res.status, count=len(tender_res.tenders))
            all_entities.extend(tender_res.entities)
            all_rels.extend(tender_res.relationships)
        except Exception as e:
            logger.exception("Tender Intelligence failed in unified profile")
            has_error = True
            response.modules.tenders = ModuleStatus(status="error", error="Tender Intelligence failed")

    if infra_task:
        try:
            infra_res = await infra_task
            response.infrastructure = infra_res["profile"]

            infra_entities = [e for e in infra_res["entities"] if e.type in ("Domain", "IPAddress", "Technology")]
            response.modules.infrastructure = ModuleStatus(
                status=infra_res["status"],
                count=len(infra_entities)
            )

            all_entities.extend(infra_res["entities"])
            all_rels.extend(infra_res["relationships"])

            org_entity = next((e for e in comp_res.entities if e.type.lower() == "organization"), None)
            dom_entity = next((e for e in infra_res["entities"] if e.type == "Domain"), None)

            if org_entity and dom_entity:
                all_rels.append(IntelligenceRelationship(
                    source=org_entity.id,
                    target=dom_entity.id,
                    type="operates",
                    confidence="high"
                ))
        except Exception as e:
            logger.exception("Infrastructure Intelligence failed in unified profile")
            has_error = True
            response.modules.infrastructure = ModuleStatus(status="error", error="Infrastructure Intelligence failed")
    # Finalize status
    if has_error:
        response.status = "partial"

    # Correlate
    try:
        c_entities, c_rels, c_clusters, c_stats = correlate_intelligence(all_entities, all_rels)
        response.entities = c_entities
        response.relationships = c_rels
        response.organization_clusters = c_clusters
        response.stats = c_stats
    except Exception as e:
        logger.exception("Correlation failed in unified profile")
        response.status = "partial"
        # We don't have a module status for correlation, but we can set top level to partial

    return response
