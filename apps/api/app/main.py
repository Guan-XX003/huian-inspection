import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models import AuditRule, Standard, StandardClause
from app.routers import admin, audit, files, quotes, reports
from app.seed import seed_database

settings = get_settings()
app = FastAPI(title=settings.app_name)

desktop_mode = os.environ.get("HUIAN_DESKTOP") == "1"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if desktop_mode else settings.cors_origin_list,
    allow_credentials=not desktop_mode,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with SessionLocal() as db:
        if not _seed_database_ready(db):
            seed_database(db)


def _seed_database_ready(db) -> bool:
    standard_count = db.scalar(select(func.count()).select_from(Standard).where(Standard.status == "active")) or 0
    rule_count = db.scalar(select(func.count()).select_from(AuditRule).where(AuditRule.status == "active")) or 0
    clause_count = db.scalar(select(func.count()).select_from(StandardClause).where(StandardClause.status == "active")) or 0
    return standard_count >= 100 and rule_count >= 100 and clause_count >= 1000


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "ocr_provider": settings.ocr_provider,
        "document_parser_provider": settings.document_parser_provider,
        "model_provider": settings.model_provider,
        "model_gateway": "litellm-compatible" if settings.litellm_base_url else "provider-base-url",
    }


app.include_router(files.router)
app.include_router(audit.router)
app.include_router(quotes.router)
app.include_router(reports.router)
app.include_router(admin.router)
