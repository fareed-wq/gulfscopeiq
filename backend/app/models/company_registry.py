from pydantic import BaseModel
from typing import Optional

class RegistryDataInput(BaseModel):
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    unified_number: Optional[str] = None
    status: Optional[str] = None
    entity_type: Optional[str] = None
    city: Optional[str] = None
    activity: Optional[str] = None
    country: Optional[str] = None
    source_url: Optional[str] = None
