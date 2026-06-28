from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IndustryBase(BaseModel):
    name: str
    code: str
    description: str = ""
    status: str = "active"


class IndustryCreate(IndustryBase):
    pass


class IndustryRead(IndustryBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class StandardBase(BaseModel):
    industry_id: str
    code: str
    name: str
    version: str = "现行"
    effective_date: str = ""
    expiry_date: str = ""
    status: str = "active"
    source_file: str = ""
    clauses: Any = []


class StandardCreate(StandardBase):
    pass


class StandardRead(StandardBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class StandardClauseRead(BaseModel):
    id: str
    standard_id: str
    industry_id: str
    clause_no: str
    title: str
    content: str
    page_no: str
    source_file: str
    chunk_index: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditRuleBase(BaseModel):
    industry_id: str
    standard_id: Optional[str] = None
    name: str
    rule_type: str = "deterministic"
    field_key: str = ""
    trigger: str = ""
    risk_level: str = "medium"
    suggestion: str = ""
    status: str = "active"


class AuditRuleCreate(AuditRuleBase):
    pass


class AuditRuleRead(AuditRuleBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class DetectionItemBase(BaseModel):
    industry_id: str
    code: str
    name: str
    method_standard: str = ""
    judgment_standard: str = ""
    price: float = 0
    cycle_days: int = 5
    sample_amount: str = ""
    package_name: str = ""
    status: str = "active"


class DetectionItemCreate(DetectionItemBase):
    pass


class DetectionItemRead(DetectionItemBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class LabBase(BaseModel):
    name: str
    qualification: str = ""
    strengths: str = ""
    status: str = "active"


class LabCreate(LabBase):
    pass


class LabRead(LabBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ModelProviderBase(BaseModel):
    provider: str
    model: str
    base_url: str = ""
    api_key_hint: str = ""
    supports_vision: bool = False
    supports_json: bool = True
    supports_tools: bool = False
    default_for_text: bool = False
    default_for_vision: bool = False
    status: str = "active"


class ModelProviderCreate(ModelProviderBase):
    api_key_secret: str = ""


class ModelProviderRead(ModelProviderBase):
    id: str
    api_key_saved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UploadedFileRead(BaseModel):
    id: str
    original_name: str
    path: str
    content_type: str
    size: int
    created_at: datetime

    class Config:
        from_attributes = True


class ImportTaskRead(BaseModel):
    id: str
    filename: str
    file_path: str
    file_type: str
    target_library: str
    status: str
    model: str
    parsed_result: Any
    error_message: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditTaskCreate(BaseModel):
    industry_id: str
    file_id: str
    customer_name: str = ""
    document_type: str = "产品标签"
    model_provider_id: Optional[str] = None
    conversation_id: Optional[str] = None


class AuditTaskUpdate(BaseModel):
    session_title: str = ""
    session_group: str = "默认分组"


class AuditTaskRead(BaseModel):
    id: str
    industry_id: str
    file_id: str
    customer_name: str
    document_type: str
    conversation_id: str = ""
    session_title: str = ""
    session_group: str = "默认分组"
    session_archived: bool = False
    status: str
    ocr_result: Any
    extracted_fields: Any
    rule_results: Any
    model_result: Any
    final_report: Any
    model_used: str
    needs_human_review: bool
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class QuoteCreate(BaseModel):
    customer_name: str = ""
    detection_item_ids: list[str] = Field(default_factory=list)
    discount_rate: float = 1
    tax_rate: float = 0.06


class QuoteRead(BaseModel):
    id: str
    quote_no: str
    audit_task_id: Optional[str]
    customer_name: str
    items_json: Any
    subtotal: float
    tax_rate: float
    discount_rate: float
    total: float
    valid_until: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    industry_count: int
    standard_count: int
    rule_count: int
    detection_item_count: int
    audit_task_count: int
    quote_count: int
    needs_review_count: int
