from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship, Evidence

class Document(BaseModel):
    id: Optional[str] = None
    title: str
    document_type: Optional[str] = None
    organization: Optional[str] = None
    country_code: Optional[str] = None
    published_at: Optional[str] = None
    source_url: Optional[str] = None
    file_url: Optional[str] = None
    mime_type: Optional[str] = None
    language: Optional[str] = None
    summary: Optional[str] = None
    evidence: List[Evidence] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)

class DocumentSearchRequest(BaseModel):
    query: str
    country_code: str
    organization: Optional[str] = None
    document_type: Optional[str] = None

    @field_validator('query')
    @classmethod
    def normalize_query(cls, v: str) -> str:
        v = ' '.join(v.split())
        if not v:
            raise ValueError('query cannot be empty')
        return v

    @field_validator('country_code')
    @classmethod
    def upper_country(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator('organization', 'document_type')
    @classmethod
    def normalize_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = ' '.join(v.split())
        return v if v else None

class DocumentSearchResponse(BaseModel):
    query: str
    country_code: str
    organization: Optional[str] = None
    document_type: Optional[str] = None
    status: str
    documents: List[Document] = Field(default_factory=list)
    entities: List[IntelligenceEntity] = Field(default_factory=list)
    relationships: List[IntelligenceRelationship] = Field(default_factory=list)
