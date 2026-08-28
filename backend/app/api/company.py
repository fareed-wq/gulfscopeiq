from fastapi import APIRouter
from app.models.intelligence import IntelligenceEntity
from app.models.company import CompanyInvestigateRequest, CompanyInvestigateResponse, Company
from app.intelligence.company_web import investigate_website
from app.intelligence.company_discovery import discover_website
from app.intelligence.company_registry import process_registry_data
from app.intelligence.company_news import discover_news

router = APIRouter()

@router.post("/investigate", response_model=CompanyInvestigateResponse)
async def investigate_company(request: CompanyInvestigateRequest):
    company = Company(
        name=request.company_name,
        normalized_name=request.company_name.lower(),
        country=request.country_code.strip() if request.country_code else None,
        registration_number=request.registration_number.strip() if request.registration_number else None
    )

    entities = []
    relationships = []

    if request.registry_data:
        await process_registry_data(request.registry_data, company, entities)

    await discover_news(company, entities, relationships)

    website_to_investigate = request.website
    if not website_to_investigate:
        website_to_investigate = await discover_website(company, request.company_name)

    if website_to_investigate:
        await investigate_website(website_to_investigate, company, entities, relationships)


    anchor_id = company.normalized_name
    if not any(e.id == anchor_id for e in entities):
        attrs = {}
        if company.country: attrs["country"] = company.country
        if company.industry: attrs["industry"] = company.industry
        if company.website: attrs["website"] = company.website
        if company.registration_number: attrs["registration_number"] = company.registration_number
        if company.status: attrs["status"] = company.status
        if company.attributes: attrs.update(company.attributes)
        
        entities.append(IntelligenceEntity(
            id=anchor_id,
            type="Organization",
            label=company.name,
            attributes=attrs
        ))

    return CompanyInvestigateResponse(

        query=request.company_name,
        company=company,
        entities=entities,
        relationships=relationships
    )
