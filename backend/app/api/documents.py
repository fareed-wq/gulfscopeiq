from fastapi import APIRouter
from app.models.document import DocumentSearchRequest, DocumentSearchResponse
from app.intelligence.corporate_ir_documents import search_corporate_ir_documents

router = APIRouter()

@router.post('/search', response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest):
    docs, ents, rels, search_status = await search_corporate_ir_documents(request)

    if not docs:
        return DocumentSearchResponse(
            query=request.query,
            country_code=request.country_code,
            organization=request.organization,
            document_type=request.document_type,
            status=search_status,
            documents=[],
            entities=[],
            relationships=[]
        )

    return DocumentSearchResponse(
        query=request.query,
        country_code=request.country_code,
        organization=request.organization,
        document_type=request.document_type,
        status='collected',
        documents=docs,
        entities=ents,
        relationships=rels
    )
