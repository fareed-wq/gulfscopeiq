from fastapi import APIRouter
from app.models.company import CompanyInvestigateRequest, CompanyInvestigateResponse, Company
from app.intelligence.company_web import investigate_website

router = APIRouter()

@router.post("/api/company/investigate", response_model=CompanyInvestigateResponse)
async def investigate_company(request: CompanyInvestigateRequest):
    company = Company(
        name=request.company_name,
        normalized_name=request.company_name.lower()
    )
    
    entities = []
    relationships = []

    if request.website:
        await investigate_website(request.website, company, entities, relationships)

    return CompanyInvestigateResponse(
        query=request.company_name,
        company=company,
        entities=entities,
        relationships=relationships
    )
