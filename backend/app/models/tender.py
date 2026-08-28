from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from app.models.intelligence import Evidence, IntelligenceEntity, IntelligenceRelationship

class Tender(BaseModel):
    id: Optional[str] = None
    title: str
    issuing_authority: Optional[str] = None
    country_code: Optional[str] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    reference_number: Optional[str] = None
    published_at: Optional[str] = None
    deadline: Optional[str] = None
    budget: Optional[str] = None
    status: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)

class TenderSearchRequest(BaseModel):
    query: str
    country_code: Optional[str] = None
    sector: Optional[str] = None

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        return ' '.join(v.split())

    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
        return v if v else None

class TenderSearchResponse(BaseModel):
    query: str
    country_code: Optional[str] = None
    status: str
    tenders: list[Tender] = Field(default_factory=list)
    entities: list[IntelligenceEntity] = Field(default_factory=list)
    relationships: list[IntelligenceRelationship] = Field(default_factory=list)
