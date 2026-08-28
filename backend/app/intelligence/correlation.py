import hashlib
import re
import unicodedata
from collections import defaultdict
from typing import List, Dict, Set, Tuple

from app.models.intelligence import IntelligenceEntity, IntelligenceRelationship
from app.models.correlation import OrganizationCluster

def normalize_organization_name(name: str) -> str:
    if not name:
        return ""
    name = unicodedata.normalize('NFKC', name)
    name = name.casefold()
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    # Normalize harmless punctuation spacing (e.g. "Company - Name" -> "Company-Name")
    name = re.sub(r'\s*([^\w\s])\s*', r'\1', name)
    return name

def _generate_deterministic_id(normalized_name: str) -> str:
    h = hashlib.sha256(normalized_name.encode('utf-8')).hexdigest()
    return f"org_{h[:16]}"

def correlate_intelligence(
    entities: List[IntelligenceEntity],
    relationships: List[IntelligenceRelationship]
) -> Tuple[List[IntelligenceEntity], List[IntelligenceRelationship], List[OrganizationCluster], dict]:
    
    org_groups: Dict[str, List[IntelligenceEntity]] = defaultdict(list)
    non_org_entities: List[IntelligenceEntity] = []
    
    for entity in entities:
        if entity.type.lower() in ("organization", "company"):
            norm_name = normalize_organization_name(entity.label)
            org_groups[norm_name].append(entity)
        else:
            non_org_entities.append(entity)
            
    canonical_entities = []
    id_mapping = {}  # old_id -> canonical_id
    
    for norm_name, group in org_groups.items():
        # Sort group deterministically to ensure first item is stable
        group.sort(key=lambda e: e.id)
        
        canonical = group[0].model_copy(deep=True)
        canonical_id = _generate_deterministic_id(norm_name)
        canonical.id = canonical_id
        
        # Merge attributes without overwriting
        for other in group[1:]:
            for k, v in (other.attributes or {}).items():
                if k not in canonical.attributes or canonical.attributes[k] is None or not str(canonical.attributes[k]).strip():
                    canonical.attributes[k] = v
        
        canonical_entities.append(canonical)
        
        for e in group:
            id_mapping[e.id] = canonical_id
            
    all_entities = canonical_entities + non_org_entities
    
    # Rewire relationships
    seen_relationships: Dict[Tuple[str, str, str], IntelligenceRelationship] = {}
    confidence_map = {"high": 3, "medium": 2, "low": 1}
    
    for rel in relationships:
        new_source = id_mapping.get(rel.source, rel.source)
        new_target = id_mapping.get(rel.target, rel.target)
        
        rel_key = (new_source, rel.type, new_target)
        if rel_key not in seen_relationships:
            new_rel = rel.model_copy(deep=True)
            new_rel.source = new_source
            new_rel.target = new_target
            seen_relationships[rel_key] = new_rel
        else:
            existing = seen_relationships[rel_key]
            
            # Merge confidence (keep highest)
            if confidence_map.get(rel.confidence, 0) > confidence_map.get(existing.confidence, 0):
                existing.confidence = rel.confidence
                
            # Merge attributes
            for k, v in (rel.attributes or {}).items():
                if k not in existing.attributes or existing.attributes[k] is None or not str(existing.attributes[k]).strip():
                    existing.attributes[k] = v
                    
            # Merge evidence
            existing_evidence_sigs = {(e.source, e.excerpt) for e in existing.evidence}
            for e in rel.evidence:
                sig = (e.source, e.excerpt)
                if sig not in existing_evidence_sigs:
                    existing.evidence.append(e)
                    existing_evidence_sigs.add(sig)

    rewired_relationships = list(seen_relationships.values())

    # Generate Organization Clusters
    clusters = []
    entity_by_id = {e.id: e for e in all_entities}
    
    for org in canonical_entities:
        connected_ids = set()
        rel_types = set()
        counts = defaultdict(int)
        
        for rel in rewired_relationships:
            connected_id = None
            if rel.source == org.id:
                connected_id = rel.target
                rel_types.add(rel.type)
            elif rel.target == org.id:
                connected_id = rel.source
                rel_types.add(rel.type)
                
            if connected_id and connected_id in entity_by_id:
                if connected_id not in connected_ids:
                    connected_ids.add(connected_id)
                    counts[entity_by_id[connected_id].type] += 1
                    
        clusters.append(OrganizationCluster(
            organization_id=org.id,
            organization_name=org.label,
            connected_entity_ids=sorted(list(connected_ids)),
            relationship_types=sorted(list(rel_types)),
            entity_type_counts=dict(counts)
        ))
        
    stats = {
        "input_entities": len(entities),
        "canonical_entities": len(all_entities),
        "input_relationships": len(relationships),
        "canonical_relationships": len(rewired_relationships),
        "organization_clusters": len(clusters)
    }
    
    # Sort for deterministic output
    all_entities.sort(key=lambda e: e.id)
    rewired_relationships.sort(key=lambda r: (r.source, r.type, r.target))
    clusters.sort(key=lambda c: c.organization_id)
    
    return all_entities, rewired_relationships, clusters, stats
