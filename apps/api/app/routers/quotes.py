from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.json_utils import loads
from app.models import AuditTask, Quote
from app.schemas import QuoteCreate, QuoteRead
from app.services.quotes import build_quote_from_items, recommend_items_for_audit

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


def serialize_quote(quote: Quote) -> QuoteRead:
    return QuoteRead.model_validate(quote, from_attributes=True).model_copy(
        update={"items_json": loads(quote.items_json, [])}
    )


@router.get("", response_model=list[QuoteRead])
def list_quotes(db: Session = Depends(get_db)) -> list[QuoteRead]:
    return [serialize_quote(item) for item in db.scalars(select(Quote).order_by(Quote.created_at.desc()))]


@router.post("", response_model=QuoteRead)
def create_quote(payload: QuoteCreate, db: Session = Depends(get_db)) -> QuoteRead:
    if not payload.detection_item_ids:
        raise HTTPException(status_code=400, detail="No detection items selected")
    try:
        quote = build_quote_from_items(
            db,
            payload.detection_item_ids,
            customer_name=payload.customer_name,
            discount_rate=payload.discount_rate,
            tax_rate=payload.tax_rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_quote(quote)


@router.post("/from-audit/{audit_id}", response_model=QuoteRead)
def create_quote_from_audit(audit_id: str, db: Session = Depends(get_db)) -> QuoteRead:
    task = db.get(AuditTask, audit_id)
    if not task:
        raise HTTPException(status_code=404, detail="Audit task not found")
    existing_quote = db.scalar(select(Quote).where(Quote.audit_task_id == task.id).order_by(Quote.created_at.desc()))
    if existing_quote:
        return serialize_quote(existing_quote)
    items = recommend_items_for_audit(db, task)
    try:
        quote = build_quote_from_items(
            db,
            [item.id for item in items],
            customer_name=task.customer_name,
            audit_task_id=task.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_quote(quote)
