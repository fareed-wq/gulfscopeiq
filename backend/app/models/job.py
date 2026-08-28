from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from app.models.intelligence import Evidence, IntelligenceEntity, IntelligenceRelationship

class Job(BaseModel):
    id: Optional[str] = None
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = None
    employment_type: Optional[str] = None
    department: Optional[str] = None
    published_at: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)

class JobSearchRequest(BaseModel):
    query: str
    country_code: Optional[str] = None
    company: Optional[str] = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return " ".join(v.split())
        
    @field_validator("company")
    @classmethod
    def validate_company(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = " ".join(v.split())
            if not v:
                return None
        return v

    @field_validator("country_code")
    @classmethod
    def uppercase_country_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
        return v

class JobSearchResponse(BaseModel):
    query: str
    country_code: Optional[str] = None
    company: Optional[str] = None
    status: str
    jobs: List[Job] = Field(default_factory=list)
    entities: List[IntelligenceEntity] = Field(default_factory=list)
    relationships: List[IntelligenceRelationship] = Field(default_factory=list)
