from fastapi import APIRouter
from app.models.tender import TenderSearchRequest, TenderSearchResponse
from app.intelligence.qatar_tenders import search_qatar_tenders

router = APIRouter()

@router.post("/api/tenders/search", response_model=TenderSearchResponse)
async def search_tenders(request: TenderSearchRequest):
    if request.country_code == "QA":
        tenders, entities, relations = await search_qatar_tenders(request.query)
        return TenderSearchResponse(
            query=request.query,
            country_code="QA",
            status="collected",
            tenders=tenders,
            entities=entities,
            relationships=relations
        )

    return TenderSearchResponse(
        query=request.query,
        country_code=request.country_code,
        status="foundation",
        tenders=[],
        entities=[],
        relationships=[]
    )
