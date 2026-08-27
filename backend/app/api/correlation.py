from fastapi import APIRouter
from app.models.correlation import CorrelationRequest, CorrelationResponse, CorrelationStats
from app.intelligence.correlation import correlate_intelligence

router = APIRouter(prefix="/api/correlation", tags=["correlation"])

@router.post("/analyze", response_model=CorrelationResponse)
async def analyze_correlation(request: CorrelationRequest):
    entities, relationships, clusters, stats_dict = correlate_intelligence(
        request.entities,
        request.relationships
    )
    
    return CorrelationResponse(
        status="correlated",
        entities=entities,
        relationships=relationships,
        organization_clusters=clusters,
        stats=CorrelationStats(**stats_dict)
    )
