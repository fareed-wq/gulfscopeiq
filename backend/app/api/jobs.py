from fastapi import APIRouter
from app.models.job import JobSearchRequest, JobSearchResponse
from app.intelligence.successfactors_jobs import search_successfactors_jobs, _match_sources

router = APIRouter()

@router.post("/api/jobs/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    if request.country_code == "SA":
        matched = _match_sources("SA", request.company)
        if matched:
            jobs, entities, relations = await search_successfactors_jobs(
                query=request.query,
                country_code="SA",
                company=request.company
            )
            return JobSearchResponse(
                query=request.query,
                country_code="SA",
                company=request.company,
                status="collected",
                jobs=jobs,
                entities=entities,
                relationships=relations
            )

    # Foundation / Unsupported
    return JobSearchResponse(
        query=request.query,
        country_code=request.country_code,
        company=request.company,
        status="foundation",
        jobs=[],
        entities=[],
        relationships=[]
    )
