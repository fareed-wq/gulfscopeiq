from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from app.models.intelligence import Evidence, IntelligenceEntity, IntelligenceRelationship
import re
import ipaddress

class InfrastructureInvestigateRequest(BaseModel):
    domain: str

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if v.startswith("http://") or v.startswith("https://"):
            v = v.split("://")[1].split("/")[0]
        if ":" in v:
            v = v.split(":")[0]
        if not v or not re.match(r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$', v):
            raise ValueError("Invalid domain")
        try:
            ipaddress.ip_address(v)
            raise ValueError("IP literals not allowed")
        except ValueError:
            pass
        if v == "localhost" or v.endswith(".local") or v.endswith(".internal"):
            raise ValueError("Private/internal targets not allowed")
        return v

class TLSSummary(BaseModel):
    issuer: str
    valid_from: str
    valid_until: str
    san_count: int
    san_names: List[str]

class IPIntelligence(BaseModel):
    ip: str
    asn: Optional[str] = None
    network_organization: Optional[str] = None
    country: Optional[str] = None

class InfrastructureProfile(BaseModel):
    domain: str
    status: str = "foundation"
    registrar: Optional[str] = None
    registered_at: Optional[str] = None
    expires_at: Optional[str] = None
    domain_status: List[str] = Field(default_factory=list)
    ipv4: List[str] = Field(default_factory=list)
    ipv6: List[str] = Field(default_factory=list)
    mx: List[str] = Field(default_factory=list)
    nameservers: List[str] = Field(default_factory=list)
    tls: Optional[TLSSummary] = None
    technologies: List[str] = Field(default_factory=list)
    ip_intelligence: List[IPIntelligence] = Field(default_factory=list)

class InfrastructureInvestigateResponse(BaseModel):
    query: str
    query_type: str = "infrastructure"
    status: str = "foundation"
    profile: InfrastructureProfile
    entities: List[IntelligenceEntity] = Field(default_factory=list)
    relationships: List[IntelligenceRelationship] = Field(default_factory=list)
