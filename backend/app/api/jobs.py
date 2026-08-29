from fastapi import APIRouter
from app.models.job import JobSearchRequest, JobSearchResponse
from app.intelligence.successfactors_jobs import search_successfactors_jobs

router = APIRouter()

@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    jobs, entities, relations, status = await search_successfactors_jobs(
        query=request.query,
        country_code=request.country_code,
        company=request.company
    )

    return JobSearchResponse(
        query=request.query,
        country_code=request.country_code,
        company=request.company,
        status=status,
        jobs=jobs,
        entities=entities,
        relationships=relations
    )
