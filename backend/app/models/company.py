from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.models.intelligence import Evidence, IntelligenceEntity, IntelligenceRelationship

class Company(BaseModel):
    name: str
    normalized_name: str
    country: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    registration_number: Optional[str] = None
    status: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)

class CompanyInvestigateRequest(BaseModel):
    company_name: str
    website: Optional[str] = None

    @field_validator('company_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError('company_name cannot be empty')
        return v

class CompanyInvestigateResponse(BaseModel):
    query: str
    query_type: str = "company"
    status: str = "foundation"
    company: Company
    entities: list[IntelligenceEntity] = Field(default_factory=list)
    relationships: list[IntelligenceRelationship] = Field(default_factory=list)
