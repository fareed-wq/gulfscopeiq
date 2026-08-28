from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.models.company import Company
from app.models.job import Job
from app.models.document import Document
from app.models.tender import Tender
from app.models.infrastructure import InfrastructureProfile
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship
from app.models.correlation import OrganizationCluster

class ModuleStatus(BaseModel):
    status: str
    count: int = 0
    error: Optional[str] = None

class UnifiedProfileModules(BaseModel):
    company: ModuleStatus
    news: ModuleStatus
    jobs: ModuleStatus
    documents: ModuleStatus
    tenders: ModuleStatus
    infrastructure: ModuleStatus

class UnifiedProfileRequest(BaseModel):
    company_name: str
    country_code: str
    query: Optional[str] = None

    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("company_name cannot be empty")
        return v

    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("country_code cannot be empty")
        return v

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = " ".join(v.split())
            if not v:
                return None
        return v

class UnifiedProfileResponse(BaseModel):
    status: str
    company_name: str
    country_code: str
    query: Optional[str] = None
    
    company: Optional[Company] = None
    infrastructure: Optional[InfrastructureProfile] = None
    
    modules: UnifiedProfileModules
    
    jobs: List[Job] = Field(default_factory=list)
    documents: List[Document] = Field(default_factory=list)
    tenders: List[Tender] = Field(default_factory=list)
    
    entities: List[IntelligenceEntity] = Field(default_factory=list)
    relationships: List[IntelligenceRelationship] = Field(default_factory=list)
    organization_clusters: List[OrganizationCluster] = Field(default_factory=list)
    
    stats: Dict[str, Any] = Field(default_factory=dict)
