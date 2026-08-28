from fastapi import APIRouter
from app.models.intelligence_profile import UnifiedProfileRequest, UnifiedProfileResponse
from app.intelligence.unified_profile import build_unified_profile

router = APIRouter()

@router.post("/api/intelligence/profile", response_model=UnifiedProfileResponse)
async def intelligence_profile(request: UnifiedProfileRequest):
    return await build_unified_profile(request)
