from fastapi import APIRouter
from app.models.job import JobSearchRequest, JobSearchResponse

router = APIRouter()

@router.post("/api/jobs/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    # Future Graph Compatibility Note:
    # Entities: Job (job), Organization (company), Location (location), Skill (skill)
    # Relationships:
    # - Job -> offered_by -> Organization
    # - Job -> located_in -> Location
    # - Company -> hiring_for -> Skill
    #
    # Do not fabricate entities or relationships yet.

    return JobSearchResponse(
        query=request.query,
        country_code=request.country_code,
        company=request.company,
        status="foundation",
        jobs=[],
        entities=[],
        relationships=[]
    )
