import logging
from app.models.company import Company
from app.models.company_registry import RegistryDataInput
from app.models.intelligence import Evidence, IntelligenceEntity

logger = logging.getLogger(__name__)

async def process_registry_data(
    registry_input: RegistryDataInput,
    company: Company,
    entities: list[IntelligenceEntity]
):
    if not registry_input:
        return

    # Normalize fields (strip whitespace and handle empty strings)
    legal_name = registry_input.legal_name.strip() if registry_input.legal_name else None
    registration_number = registry_input.registration_number.strip() if registry_input.registration_number else None
    unified_number = registry_input.unified_number.strip() if registry_input.unified_number else None
    status = registry_input.status.strip() if registry_input.status else None
    entity_type = registry_input.entity_type.strip() if registry_input.entity_type else None
    city = registry_input.city.strip() if registry_input.city else None
    activity = registry_input.activity.strip() if registry_input.activity else None
    country = registry_input.country.strip() if registry_input.country else None
    source_url = registry_input.source_url.strip() if registry_input.source_url else None
    
    source_label = "Supplied Registry Data"
    
    evidence = Evidence(
        source=source_label,
        source_url=source_url,
        excerpt="Structured public registry data (user-supplied or openly obtained)."
    )
    
    if "registry" not in company.attributes:
        company.attributes["registry"] = {}
        
    company.attributes["registry"].update({
        "legal_name": legal_name,
        "registration_number": registration_number,
        "unified_number": unified_number,
        "status": status,
        "entity_type": entity_type,
        "city": city,
        "activity": activity,
        "country": country,
        "source_url": source_url,
        "verified_via_external_api": False
    })
    
    company.evidence.append(evidence)
    
    if registration_number:
        company.registration_number = registration_number
        entities.append(IntelligenceEntity(
            id=f"reg_{registration_number}",
            type="registration_number",
            label=registration_number,
            evidence=[evidence]
        ))
        
    if unified_number:
        entities.append(IntelligenceEntity(
            id=f"unified_{unified_number}",
            type="unified_number",
            label=unified_number,
            evidence=[evidence]
        ))
        
    if legal_name:
        entities.append(IntelligenceEntity(
            id=f"legal_name_{legal_name.lower().replace(' ', '_')}",
            type="legal_name",
            label=legal_name,
            evidence=[evidence]
        ))
