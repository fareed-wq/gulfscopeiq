from fastapi import APIRouter
from app.models.company import CompanyInvestigateRequest, CompanyInvestigateResponse, Company
from app.intelligence.company_web import investigate_website
from app.intelligence.company_discovery import discover_website

router = APIRouter()

@router.post("/api/company/investigate", response_model=CompanyInvestigateResponse)
async def investigate_company(request: CompanyInvestigateRequest):
    company = Company(
        name=request.company_name,
        normalized_name=request.company_name.lower()
    )
    
    entities = []
    relationships = []

    website_to_investigate = request.website
    if not website_to_investigate:
        website_to_investigate = await discover_website(company, request.company_name)

    if website_to_investigate:
        await investigate_website(website_to_investigate, company, entities, relationships)

    return CompanyInvestigateResponse(
        query=request.company_name,
        company=company,
        entities=entities,
        relationships=relationships
    )
