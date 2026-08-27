from fastapi import APIRouter
from app.models.company import CompanyInvestigateRequest, CompanyInvestigateResponse, Company

router = APIRouter()

@router.post("/api/company/investigate", response_model=CompanyInvestigateResponse)
async def investigate_company(request: CompanyInvestigateRequest):
    company = Company(
        name=request.company_name,
        normalized_name=request.company_name.lower()
    )
    
    return CompanyInvestigateResponse(
        query=request.company_name,
        company=company
    )
