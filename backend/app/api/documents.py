from fastapi import APIRouter
from app.models.document import DocumentSearchRequest, DocumentSearchResponse

router = APIRouter()

@router.post('/search', response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest):
    return DocumentSearchResponse(
        query=request.query,
        country_code=request.country_code,
        organization=request.organization,
        document_type=request.document_type,
        status='foundation',
        documents=[],
        entities=[],
        relationships=[]
    )
