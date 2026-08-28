import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.models.company import Company
from app.models.company_registry import RegistryDataInput
from app.intelligence.company_registry import process_registry_data

def test_process_registry_data_valid_saudi():
    company = Company(name="Saudi Aramco", normalized_name="saudi aramco")
    entities = []
    
    registry_input = RegistryDataInput(
        legal_name=" Saudi Arabian Oil Company ",
        registration_number=" 2052101150 ",
        unified_number=" 7001491415 ",
        status=" Active ",
        entity_type=" Joint Stock Company ",
        city=" Dhahran ",
        activity=" Oil & Gas Exploration ",
        country=" SA ",
        source_url=" https://mc.gov.sa/fake/2052101150 "
    )
    
    asyncio.run(process_registry_data(registry_input, company, entities))
    
    # Check normalization
    reg = company.attributes["registry"]
    assert reg["legal_name"] == "Saudi Arabian Oil Company"
    assert reg["registration_number"] == "2052101150"
    assert reg["unified_number"] == "7001491415"
    assert reg["status"] == "Active"
    assert reg["entity_type"] == "Joint Stock Company"
    assert reg["city"] == "Dhahran"
    assert reg["activity"] == "Oil & Gas Exploration"
    assert reg["country"] == "SA"
    assert reg["source_url"] == "https://mc.gov.sa/fake/2052101150"
    assert reg["verified_via_external_api"] is False
    
    # Check evidence attached
    assert len(company.evidence) > 0
    assert company.evidence[0].source == "Supplied Registry Data"
    assert company.evidence[0].source_url == "https://mc.gov.sa/fake/2052101150"
    
    # Check entities created
    reg_entity = next(e for e in entities if e.type == "registration_number")
    assert reg_entity.label == "2052101150"
    assert company.registration_number == "2052101150"
    
    unified_entity = next(e for e in entities if e.type == "unified_number")
    assert unified_entity.label == "7001491415"
    
    legal_entity = next(e for e in entities if e.type == "legal_name")
    assert legal_entity.label == "Saudi Arabian Oil Company"

def test_process_registry_data_missing_fields():
    company = Company(name="Example", normalized_name="example")
    entities = []
    
    registry_input = RegistryDataInput(
        registration_number="123456"
    )
    
    asyncio.run(process_registry_data(registry_input, company, entities))
    
    reg = company.attributes["registry"]
    assert reg["registration_number"] == "123456"
    assert reg["legal_name"] is None
    assert reg["city"] is None
    
    reg_entity = next(e for e in entities if e.type == "registration_number")
    assert reg_entity.label == "123456"

def test_process_registry_data_none():
    company = Company(name="Example", normalized_name="example")
    entities = []
    asyncio.run(process_registry_data(None, company, entities))
    assert "registry" not in company.attributes
    assert len(entities) == 0
