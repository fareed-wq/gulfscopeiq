import pytest
from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship, Evidence
from app.intelligence.correlation import (
    correlate_intelligence,
    normalize_organization_name,
    _generate_deterministic_id
)

def test_normalization_rules():
    assert normalize_organization_name("SABIC") == "sabic"
    assert normalize_organization_name("sabic") == "sabic"
    assert normalize_organization_name("  SABIC  ") == "sabic"
    assert normalize_organization_name("Saudi   Aramco") == "saudi aramco"
    assert normalize_organization_name("saudi aramco") == "saudi aramco"
    
    # New spacing punctuation rules
    assert normalize_organization_name("Company - Name") == "company-name"
    assert normalize_organization_name("Company-Name") == "company-name"
    assert normalize_organization_name("Company & Partners") == "company&partners"
    assert normalize_organization_name("Company  &  Partners") == "company&partners"
    
    # Must remain distinct unless identical after spacing normalization
    assert normalize_organization_name("ABC Holdings") == "abc holdings"
    assert normalize_organization_name("ABC-Holdings") == "abc-holdings"
    assert normalize_organization_name("ABC Holdings") != normalize_organization_name("ABC-Holdings")

    assert normalize_organization_name("STC") == "stc"
    assert normalize_organization_name("Saudi Telecom Company") == "saudi telecom company"
    assert normalize_organization_name("STC") != normalize_organization_name("Saudi Telecom Company")

    assert normalize_organization_name("Aramco") == "aramco"
    assert normalize_organization_name("Saudi Aramco") == "saudi aramco"
    assert normalize_organization_name("Aramco") != normalize_organization_name("Saudi Aramco")


def test_deterministic_canonical_ids():
    norm_name = normalize_organization_name("SABIC")
    expected_id = _generate_deterministic_id(norm_name)
    
    e1 = IntelligenceEntity(id="z_org", type="Organization", label="SABIC")
    e2 = IntelligenceEntity(id="a_org", type="Organization", label="sabic")
    
    # Run forward
    entities, rels, clusters, stats = correlate_intelligence([e1, e2], [])
    assert len(entities) == 1
    assert entities[0].id == expected_id
    
    # Reversing input order gives identical output
    entities_rev, rels_rev, clusters_rev, stats_rev = correlate_intelligence([e2, e1], [])
    assert len(entities_rev) == 1
    assert entities_rev[0].id == expected_id
    assert entities_rev[0].label == entities[0].label


def test_same_org_different_casing_merges():
    e1 = IntelligenceEntity(id="1", type="Organization", label="SABIC", attributes={"k1": "v1"})
    e2 = IntelligenceEntity(id="2", type="Organization", label="sabic", attributes={"k2": "v2", "k1": "conflict"})
    
    entities, rels, clusters, stats = correlate_intelligence([e1, e2], [])
    
    assert len(entities) == 1
    assert entities[0].label == "SABIC"
    # k1 should be v1 because it preserves first non-empty value encountered and does not overwrite with conflict
    assert entities[0].attributes == {"k1": "v1", "k2": "v2"}
    assert stats["canonical_entities"] == 1


def test_different_orgs_remain_separate():
    e1 = IntelligenceEntity(id="1", type="Organization", label="SABIC")
    e2 = IntelligenceEntity(id="2", type="Organization", label="Aramco")
    
    entities, rels, clusters, stats = correlate_intelligence([e1, e2], [])
    assert len(entities) == 2
    assert len(clusters) == 2


def test_non_orgs_never_merge():
    e1 = IntelligenceEntity(id="1", type="Job", label="Software Engineer")
    e2 = IntelligenceEntity(id="2", type="Job", label="Software Engineer")
    
    entities, rels, clusters, stats = correlate_intelligence([e1, e2], [])
    assert len(entities) == 2
    assert len(clusters) == 0


def test_relationship_endpoints_rewired_correctly():
    e1 = IntelligenceEntity(id="org1", type="Organization", label="SABIC")
    e2 = IntelligenceEntity(id="org2", type="Organization", label="sabic")
    j1 = IntelligenceEntity(id="job1", type="Job", label="Engineer")
    
    rel = IntelligenceRelationship(source="org2", target="job1", type="posts_job", confidence="high")
    
    entities, rels, clusters, stats = correlate_intelligence([e1, e2, j1], [rel])
    
    assert len(entities) == 2  # 1 org, 1 job
    assert len(rels) == 1
    
    canonical_org = [e for e in entities if e.type.lower() in ("organization", "company")][0]
    
    assert rels[0].source == canonical_org.id
    assert rels[0].target == "job1"


def test_duplicate_edges_do_not_inflate_cluster_counts():
    e1 = IntelligenceEntity(id="org1", type="Organization", label="SABIC")
    j1 = IntelligenceEntity(id="job1", type="Job", label="Engineer")
    
    rel1 = IntelligenceRelationship(source="org1", target="job1", type="posts_job", confidence="medium", attributes={"a": 1}, evidence=[Evidence(source="s1")])
    rel2 = IntelligenceRelationship(source="org1", target="job1", type="posts_job", confidence="high", attributes={"b": 2}, evidence=[Evidence(source="s2")])
    
    entities, rels, clusters, stats = correlate_intelligence([e1, j1], [rel1, rel2])
    
    # Dedup check
    assert len(rels) == 1
    assert rels[0].confidence == "high"
    assert rels[0].attributes == {"a": 1, "b": 2}
    assert len(rels[0].evidence) == 2
    
    # Cluster counts unique connected entities, so it should be exactly 1
    assert len(clusters) == 1
    assert clusters[0].entity_type_counts.get("Job") == 1
    assert clusters[0].connected_entity_ids == ["job1"]


def test_organization_cluster_counts_and_connections():
    org = IntelligenceEntity(id="org1", type="Organization", label="SABIC")
    j1 = IntelligenceEntity(id="job1", type="Job", label="J1")
    j2 = IntelligenceEntity(id="job2", type="Job", label="J2")
    d1 = IntelligenceEntity(id="doc1", type="Document", label="D1")
    t1 = IntelligenceEntity(id="tender1", type="Tender", label="T1")
    
    r1 = IntelligenceRelationship(source="org1", target="job1", type="posts_job", confidence="high")
    r2 = IntelligenceRelationship(source="org1", target="job2", type="posts_job", confidence="high")
    r3 = IntelligenceRelationship(source="org1", target="doc1", type="published_document", confidence="high")
    r4 = IntelligenceRelationship(source="org1", target="tender1", type="has_tender", confidence="high")
    
    entities, rels, clusters, stats = correlate_intelligence([org, j1, j2, d1, t1], [r1, r2, r3, r4])
    
    assert len(clusters) == 1
    c = clusters[0]
    canonical_org_id = _generate_deterministic_id(normalize_organization_name("SABIC"))
    assert c.organization_id == canonical_org_id
    assert c.entity_type_counts.get("Job") == 2
    assert c.entity_type_counts.get("Document") == 1
    assert c.entity_type_counts.get("Tender") == 1
    assert len(c.connected_entity_ids) == 4
    assert len(c.relationship_types) == 3


def test_isolated_organization_cluster():
    org = IntelligenceEntity(id="org1", type="Organization", label="SABIC")
    entities, rels, clusters, stats = correlate_intelligence([org], [])
    
    assert len(clusters) == 1
    assert clusters[0].entity_type_counts == {}
    assert clusters[0].connected_entity_ids == []
    
    
def test_empty_input():
    entities, rels, clusters, stats = correlate_intelligence([], [])
    assert len(entities) == 0
    assert len(rels) == 0
    assert len(clusters) == 0
    assert stats["input_entities"] == 0


def test_cross_module_org_types_correlate():
    e1 = IntelligenceEntity(id="1", type="Organization", label="SABIC")
    e2 = IntelligenceEntity(id="2", type="organization", label="sabic")
    e3 = IntelligenceEntity(id="3", type="Company", label="SABIC")
    e4 = IntelligenceEntity(id="4", type="company", label="SABIC")
    
    entities, rels, clusters, stats = correlate_intelligence([e1, e2, e3, e4], [])
    
    assert len(entities) == 1
    assert entities[0].type == "Organization"  # Takes the first one's type
    assert len(clusters) == 1
    assert stats["canonical_entities"] == 1
