from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship

class CorrelationStats(BaseModel):
    input_entities: int
    canonical_entities: int
    input_relationships: int
    canonical_relationships: int
    organization_clusters: int

class OrganizationCluster(BaseModel):
    organization_id: str
    organization_name: str
    connected_entity_ids: List[str]
    relationship_types: List[str]
    entity_type_counts: Dict[str, int]

class CorrelationRequest(BaseModel):
    entities: List[IntelligenceEntity]
    relationships: List[IntelligenceRelationship]

class CorrelationResponse(BaseModel):
    status: str = "correlated"
    entities: List[IntelligenceEntity]
    relationships: List[IntelligenceRelationship]
    organization_clusters: List[OrganizationCluster]
    stats: CorrelationStats
