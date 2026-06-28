from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return uuid4().hex


class Status(str, Enum):
    active = "active"
    inactive = "inactive"


class ReviewStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    needs_review = "needs_review"
    failed = "failed"


class Industry(Base):
    __tablename__ = "industries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=Status.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Standard(Base):
    __tablename__ = "standards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"))
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[str] = mapped_column(String(40), default="现行")
    effective_date: Mapped[str] = mapped_column(String(20), default="")
    expiry_date: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default=Status.active.value)
    source_file: Mapped[str] = mapped_column(String(260), default="")
    clauses: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    industry: Mapped[Industry] = relationship()


class StandardClause(Base):
    __tablename__ = "standard_clauses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    standard_id: Mapped[str] = mapped_column(ForeignKey("standards.id"), index=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"), index=True)
    clause_no: Mapped[str] = mapped_column(String(80), default="", index=True)
    title: Mapped[str] = mapped_column(String(240), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    page_no: Mapped[str] = mapped_column(String(40), default="")
    source_file: Mapped[str] = mapped_column(String(360), default="")
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=Status.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    standard: Mapped[Standard] = relationship()
    industry: Mapped[Industry] = relationship()


class AuditRule(Base):
    __tablename__ = "audit_rules"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"))
    standard_id: Mapped[Optional[str]] = mapped_column(ForeignKey("standards.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    rule_type: Mapped[str] = mapped_column(String(40), default="deterministic")
    field_key: Mapped[str] = mapped_column(String(80), default="")
    trigger: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(20), default="medium")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=Status.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    industry: Mapped[Industry] = relationship()
    standard: Mapped[Optional[Standard]] = relationship()


class FieldTemplate(Base):
    __tablename__ = "field_templates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"), unique=True)
    fields_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    industry: Mapped[Industry] = relationship()


class DetectionItem(Base):
    __tablename__ = "detection_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"))
    code: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(160))
    method_standard: Mapped[str] = mapped_column(String(120), default="")
    judgment_standard: Mapped[str] = mapped_column(String(120), default="")
    price: Mapped[float] = mapped_column(Float, default=0)
    cycle_days: Mapped[int] = mapped_column(Integer, default=5)
    sample_amount: Mapped[str] = mapped_column(String(80), default="")
    package_name: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default=Status.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    industry: Mapped[Industry] = relationship()


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    qualification: Mapped[str] = mapped_column(String(200), default="")
    strengths: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=Status.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelProvider(Base):
    __tablename__ = "model_providers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(120))
    base_url: Mapped[str] = mapped_column(String(260), default="")
    api_key_hint: Mapped[str] = mapped_column(String(120), default="")
    api_key_secret: Mapped[str] = mapped_column(Text, default="")
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_json: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False)
    default_for_text: Mapped[bool] = mapped_column(Boolean, default=False)
    default_for_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default=Status.active.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def api_key_saved(self) -> bool:
        return bool((self.api_key_secret or "").strip())


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    original_name: Mapped[str] = mapped_column(String(260))
    path: Mapped[str] = mapped_column(String(360))
    content_type: Mapped[str] = mapped_column(String(120), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ImportTask(Base):
    __tablename__ = "import_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    filename: Mapped[str] = mapped_column(String(260))
    file_path: Mapped[str] = mapped_column(String(360), default="")
    file_type: Mapped[str] = mapped_column(String(40), default="")
    target_library: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(30), default="completed")
    model: Mapped[str] = mapped_column(String(160), default="local-parser")
    parsed_result: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditTask(Base):
    __tablename__ = "audit_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"))
    file_id: Mapped[str] = mapped_column(ForeignKey("uploaded_files.id"))
    customer_name: Mapped[str] = mapped_column(String(120), default="")
    document_type: Mapped[str] = mapped_column(String(80), default="产品标签")
    conversation_id: Mapped[str] = mapped_column(String(32), index=True, default=new_id)
    session_title: Mapped[str] = mapped_column(String(160), default="")
    session_group: Mapped[str] = mapped_column(String(80), default="默认分组")
    session_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default=ReviewStatus.pending.value)
    ocr_result: Mapped[str] = mapped_column(Text, default="{}")
    extracted_fields: Mapped[str] = mapped_column(Text, default="{}")
    rule_results: Mapped[str] = mapped_column(Text, default="[]")
    model_result: Mapped[str] = mapped_column(Text, default="{}")
    final_report: Mapped[str] = mapped_column(Text, default="{}")
    model_used: Mapped[str] = mapped_column(String(160), default="")
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    industry: Mapped[Industry] = relationship()
    file: Mapped[UploadedFile] = relationship()


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    quote_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    audit_task_id: Mapped[Optional[str]] = mapped_column(ForeignKey("audit_tasks.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(120), default="")
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.06)
    discount_rate: Mapped[float] = mapped_column(Float, default=1)
    total: Mapped[float] = mapped_column(Float, default=0)
    valid_until: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    audit_task: Mapped[Optional[AuditTask]] = relationship()
