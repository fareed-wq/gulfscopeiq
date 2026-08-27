from fastapi import APIRouter
from app.models.tender import TenderSearchRequest, TenderSearchResponse

router = APIRouter()

@router.post("/api/tenders/search", response_model=TenderSearchResponse)
async def search_tenders(request: TenderSearchRequest):
    return TenderSearchResponse(
        query=request.query,
        country_code=request.country_code,
        status="foundation",
        tenders=[],
        entities=[],
        relationships=[]
    )
