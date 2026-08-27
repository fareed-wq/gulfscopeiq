from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.company import router as company_router

app = FastAPI(title="GulfScopeIQ API")

app.include_router(health_router)
app.include_router(company_router)
