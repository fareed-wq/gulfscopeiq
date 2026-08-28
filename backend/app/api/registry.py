from fastapi import APIRouter
from typing import Dict
from app.registry.gcc import GCC_REGISTRY, CountryRegistryEntry

router = APIRouter()

@router.get("/gcc", response_model=Dict[str, CountryRegistryEntry])
async def get_gcc_registry():
    return GCC_REGISTRY
