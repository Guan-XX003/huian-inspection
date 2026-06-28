from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditTask, Quote
from app.services.reports import generate_audit_pdf, generate_quote_pdf, generate_quote_xlsx

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/audit/{task_id}/download")
def download_audit_report(task_id: str, db: Session = Depends(get_db)) -> FileResponse:
    task = db.get(AuditTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Audit task not found")
    path = generate_audit_pdf(task)
    return FileResponse(path, filename=f"audit-{task.id}.pdf")


@router.get("/quotes/{quote_id}/download")
def download_quote_report(quote_id: str, fmt: str = "pdf", db: Session = Depends(get_db)) -> FileResponse:
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    if fmt == "xlsx":
        path = generate_quote_xlsx(quote)
        return FileResponse(path, filename=f"quote-{quote.quote_no}.xlsx")
    path = generate_quote_pdf(quote)
    return FileResponse(path, filename=f"quote-{quote.quote_no}.pdf")

