from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.company import router as company_router
from app.api.tender import router as tender_router
from app.api.jobs import router as jobs_router

app = FastAPI(title="GulfScopeIQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(company_router)
app.include_router(tender_router)
app.include_router(jobs_router)
