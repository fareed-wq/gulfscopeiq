from enum import Enum
from typing import List, Dict
from pydantic import BaseModel, Field

class SourceStatus(str, Enum):
    configured = "configured"
    foundation = "foundation"
    unavailable = "unavailable"

class OrganizationCapabilities(BaseModel):
    documents: SourceStatus = SourceStatus.foundation
    jobs: SourceStatus = SourceStatus.foundation

class OrganizationRegistryEntry(BaseModel):
    organization_id: str
    organization_name: str
    aliases: List[str] = Field(default_factory=list)
    capabilities: OrganizationCapabilities

class CountryRegistryEntry(BaseModel):
    country_code: str
    country_name: str
    tenders: SourceStatus = SourceStatus.foundation
    organizations: List[OrganizationRegistryEntry] = Field(default_factory=list)

GCC_REGISTRY: Dict[str, CountryRegistryEntry] = {
    "SA": CountryRegistryEntry(
        country_code="SA",
        country_name="Saudi Arabia",
        tenders=SourceStatus.foundation,
        organizations=[
            OrganizationRegistryEntry(
                organization_id="sabic",
                organization_name="SABIC",
                aliases=["sabic"],
                capabilities=OrganizationCapabilities(
                    documents=SourceStatus.configured,
                    jobs=SourceStatus.configured
                )
            ),
            OrganizationRegistryEntry(
                organization_id="saudi_aramco",
                organization_name="Saudi Aramco",
                aliases=["aramco"],
                capabilities=OrganizationCapabilities(
                    jobs=SourceStatus.configured
                )
            ),
            OrganizationRegistryEntry(
                organization_id="stc",
                organization_name="STC",
                aliases=["saudi telecom company", "saudi telecom"],
                capabilities=OrganizationCapabilities(
                    jobs=SourceStatus.configured
                )
            )
        ]
    ),
    "AE": CountryRegistryEntry(
        country_code="AE",
        country_name="United Arab Emirates",
        tenders=SourceStatus.unavailable
    ),
    "QA": CountryRegistryEntry(
        country_code="QA",
        country_name="Qatar",
        tenders=SourceStatus.configured
    ),
    "KW": CountryRegistryEntry(
        country_code="KW",
        country_name="Kuwait",
        tenders=SourceStatus.configured
    ),
    "BH": CountryRegistryEntry(
        country_code="BH",
        country_name="Bahrain",
        tenders=SourceStatus.configured
    ),
    "OM": CountryRegistryEntry(
        country_code="OM",
        country_name="Oman",
        tenders=SourceStatus.foundation
    )
}
