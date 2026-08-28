from pydantic import BaseModel, Field
from typing import Optional, Literal, Any

class Evidence(BaseModel):
    source: str
    source_url: Optional[str] = None
    excerpt: Optional[str] = None

class IntelligenceEntity(BaseModel):
    id: str
    type: str
    label: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)

class IntelligenceRelationship(BaseModel):
    source: str
    target: str
    type: str
    confidence: Literal["high", "medium", "low"]
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)

class IntelligenceReport(BaseModel):
    query: str
    query_type: str
    entities: list[IntelligenceEntity] = Field(default_factory=list)
    relationships: list[IntelligenceRelationship] = Field(default_factory=list)
