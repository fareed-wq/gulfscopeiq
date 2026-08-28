import pytest
from app.models.intelligence import (
    Evidence,
    IntelligenceEntity,
    IntelligenceRelationship,
    IntelligenceReport
)

def test_entity_creation():
    entity = IntelligenceEntity(
        id="ent-1",
        type="company",
        label="Saudi Aramco"
    )
    assert entity.id == "ent-1"
    assert entity.attributes == {}
    assert entity.evidence == []

def test_relationship_with_evidence_and_confidence():
    evidence = Evidence(source="News", source_url="http://example.com")
    rel = IntelligenceRelationship(
        source="ent-1",
        target="ent-2",
        type="subsidiary",
        confidence="high",
        evidence=[evidence]
    )
    assert rel.confidence == "high"
    assert len(rel.evidence) == 1
    assert rel.evidence[0].source == "News"
    
def test_empty_defaults_are_independent():
    entity1 = IntelligenceEntity(id="e1", type="t", label="l")
    entity2 = IntelligenceEntity(id="e2", type="t", label="l")
    entity1.attributes["key"] = "value"
    entity1.evidence.append(Evidence(source="Test"))
    assert entity2.attributes == {}
    assert entity2.evidence == []

def test_full_report_serialization():
    report = IntelligenceReport(
        query="oil companies",
        query_type="market_scan",
        entities=[
            IntelligenceEntity(id="c1", type="company", label="Company A")
        ],
        relationships=[
            IntelligenceRelationship(
                source="c1",
                target="c2",
                type="competitor",
                confidence="medium"
            )
        ]
    )
    
    data = report.model_dump()
    assert data["query"] == "oil companies"
    assert len(data["entities"]) == 1
    assert data["entities"][0]["id"] == "c1"
    assert len(data["relationships"]) == 1
    assert data["relationships"][0]["confidence"] == "medium"
    
    json_str = report.model_dump_json()
    assert "Company A" in json_str
