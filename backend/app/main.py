from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.company import router as company_router
from app.api.tender import router as tender_router
from app.api.jobs import router as jobs_router
from app.api.documents import router as documents_router
from app.api.correlation import router as correlation_router
from app.api.intelligence_profile import router as profile_router
from app.api.infrastructure import router as infrastructure_router
from app.api.registry import router as registry_router

app = FastAPI(title="GulfScopeIQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(company_router, prefix="/api/company", tags=["company"])
app.include_router(tender_router, prefix="/api/tenders", tags=["tenders"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(correlation_router, prefix="/api/correlation", tags=["correlation"])

app.include_router(profile_router, tags=["profile"])
app.include_router(infrastructure_router, tags=["infrastructure"])
app.include_router(registry_router, prefix="/api/registry", tags=["registry"])
