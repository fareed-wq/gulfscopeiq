from fastapi import APIRouter, HTTPException
from app.models.infrastructure import InfrastructureInvestigateRequest, InfrastructureInvestigateResponse
from app.intelligence.infrastructure import investigate_infrastructure
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/infrastructure/investigate", response_model=InfrastructureInvestigateResponse)
async def investigate_infrastructure_endpoint(request: InfrastructureInvestigateRequest):
    try:
        domain = request.domain
        result = await investigate_infrastructure(domain)
        
        return InfrastructureInvestigateResponse(
            query=domain,
            status=result["status"],
            profile=result["profile"],
            entities=result["entities"],
            relationships=result["relationships"]
        )
    except Exception as e:
        logger.error(f"Infrastructure investigation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
