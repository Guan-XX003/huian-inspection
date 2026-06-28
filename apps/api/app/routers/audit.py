from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.json_utils import dumps, loads
from app.models import AuditRule, AuditTask, FieldTemplate, Industry, ModelProvider, ReviewStatus, StandardClause, UploadedFile
from app.schemas import AuditTaskCreate, AuditTaskRead, AuditTaskUpdate
from app.services.extraction import extract_fields
from app.services.industry_router import classify_industry_code
from app.services.model_gateway import get_model_gateway
from app.services.ocr import get_ocr_adapter
from app.services.quotes import recommend_items_for_audit
from app.services.rule_engine import evaluate_rules

router = APIRouter(prefix="/api/audit", tags=["audit"])


def serialize_task(task: AuditTask) -> AuditTaskRead:
    return AuditTaskRead.model_validate(task, from_attributes=True).model_copy(
        update={
            "ocr_result": loads(task.ocr_result, {}),
            "extracted_fields": loads(task.extracted_fields, {}),
            "rule_results": loads(task.rule_results, []),
            "model_result": loads(task.model_result, {}),
            "final_report": loads(task.final_report, {}),
        }
    )


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return dumps(value)
    return str(value)


def _normalize_findings(
    findings: list[dict],
    rule_results: list[dict],
    fields: dict,
    ocr_result: dict,
    recommended_item_codes: list[str],
    default_confidence: float,
) -> list[dict]:
    rule_by_name = {item.get("rule_name"): item for item in rule_results if isinstance(item, dict)}
    normalized = []
    seen_titles: set[str] = set()
    seen_rule_keys: set[tuple[str, str, str]] = set()
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            continue
        matched_rule = rule_by_name.get(finding.get("title")) or {}
        field_key = str(finding.get("field_key") or matched_rule.get("field_key") or "")
        title = str(finding.get("title") or matched_rule.get("rule_name") or "风险提示")
        if title in seen_titles:
            continue
        risk_level = str(finding.get("risk_level") or matched_rule.get("risk_level") or "medium")
        if _is_compliant_finding(title, risk_level, finding):
            continue
        evidence_text = _stringify(finding.get("evidence_text") or fields.get(field_key) or ocr_result.get("text", "")[:280])
        confidence = finding.get("confidence")
        try:
            confidence_value = float(confidence) if confidence not in ("", None) else float(default_confidence)
        except (TypeError, ValueError):
            confidence_value = float(default_confidence)
        if confidence_value > 1:
            confidence_value = confidence_value / 100
        confidence_value = max(0, min(confidence_value, 1))
        standard_code = str(finding.get("standard_code") or matched_rule.get("standard") or "")
        standard_clause = str(finding.get("standard_clause") or matched_rule.get("standard_clause") or "")
        rule_key = (field_key, standard_code, risk_level)
        if field_key and standard_code and rule_key in seen_rule_keys:
            continue
        source_excerpt = str(
            finding.get("source_excerpt")
            or matched_rule.get("source_excerpt")
            or matched_rule.get("detail")
            or ""
        )
        source_excerpt = _clean_source_excerpt(source_excerpt)
        if title == "模型风险提示" and not standard_code and source_excerpt == "":
            continue
        normalized.append(
            {
                "finding_id": str(finding.get("finding_id") or f"F-{index + 1:03d}"),
                "title": title,
                "risk_level": risk_level,
                "field_key": field_key,
                "evidence_text": evidence_text,
                "reason": str(finding.get("reason") or matched_rule.get("detail") or "模型或规则识别到潜在风险。"),
                "suggestion": str(finding.get("suggestion") or matched_rule.get("suggestion") or "建议人工复核并结合现行标准确认。"),
                "standard_code": standard_code,
                "standard_clause": standard_clause,
                "source_excerpt": source_excerpt or "依据标准规则库匹配结果生成，需结合源文件条款复核。",
                "confidence": round(confidence_value, 2),
                "needs_human_review": bool(
                    finding.get("needs_human_review")
                    or risk_level == "high"
                    or confidence_value < 0.82
                ),
                "recommended_item_codes": finding.get("recommended_item_codes") or recommended_item_codes,
            }
        )
        seen_titles.add(title)
        if field_key and standard_code:
            seen_rule_keys.add(rule_key)
    return normalized


def _is_compliant_finding(title: str, risk_level: str, finding: dict) -> bool:
    if risk_level != "low":
        return False
    positive_markers = ["齐全", "完整", "符合", "通过", "可识别", "已识别", "已标示", "未发现"]
    title_negative_markers = ["不足", "缺失", "不清晰", "不明确", "无法", "未在", "疑似", "风险", "不一致", "不规范"]
    if any(marker in title for marker in positive_markers) and not any(marker in title for marker in title_negative_markers):
        return True
    text = " ".join(
        _stringify(finding.get(key, ""))
        for key in ["title", "reason", "evidence_text", "suggestion"]
    )
    negative_markers = ["不足", "缺失", "不清晰", "不明确", "无法", "未在", "疑似", "风险", "不一致", "不规范"]
    if any(marker in text for marker in negative_markers):
        return False
    return any(marker in title or marker in text for marker in positive_markers)


def _clean_source_excerpt(value: str) -> str:
    text = " ".join(str(value or "").split())
    text = text.replace(" . ", ".").replace(" ％", "%")
    return text[:700]


def _is_image_file(file_path: str) -> bool:
    return str(file_path).lower().rsplit(".", 1)[-1] in {"jpg", "jpeg", "png", "bmp", "webp", "tif", "tiff"}


def _rules_as_vision_checklist(rule_results: list[dict]) -> list[dict]:
    checklist = []
    for item in rule_results:
        checklist.append(
            {
                **item,
                "passed": True,
                "detail": (
                    "视觉模型优先识别图片原文后再核验该项；"
                    "不要把 OCR 或初步字段抽取为空直接判定为缺失。"
                ),
                "suggestion": "",
                "vision_check_required": True,
            }
        )
    return checklist


@router.get("/tasks", response_model=list[AuditTaskRead])
def list_tasks(db: Session = Depends(get_db)) -> list[AuditTaskRead]:
    tasks = list(db.scalars(select(AuditTask).where(AuditTask.session_archived.is_(False)).order_by(AuditTask.created_at.desc())))
    return [serialize_task(task) for task in tasks]


@router.post("/tasks", response_model=AuditTaskRead)
def create_task(payload: AuditTaskCreate, db: Session = Depends(get_db)) -> AuditTaskRead:
    file = db.get(UploadedFile, payload.file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    ocr_result = get_ocr_adapter().analyze(file.path)
    industry = db.get(Industry, payload.industry_id)
    if not industry and payload.industry_id in {"auto", "", "AUTO"}:
        industry_code = classify_industry_code(ocr_result.get("text", ""))
        industry = db.scalar(select(Industry).where(Industry.code == industry_code, Industry.status == "active"))
        ocr_result["auto_classified_industry"] = industry_code
    if not industry:
        raise HTTPException(status_code=404, detail="Industry not found")

    force_local_model = payload.model_provider_id in {"local", "mock", "none"}
    provider = (
        db.get(ModelProvider, payload.model_provider_id)
        if payload.model_provider_id and not force_local_model
        else None
    )
    if not provider and not force_local_model:
        provider = db.scalar(
            select(ModelProvider).where(ModelProvider.default_for_text.is_(True), ModelProvider.status == "active")
        )

    task = AuditTask(
        industry_id=industry.id,
        file_id=file.id,
        customer_name=payload.customer_name,
        document_type=payload.document_type,
        session_group=payload.document_type or "默认分组",
        status=ReviewStatus.pending.value,
    )
    db.add(task)
    db.flush()

    template = db.scalar(select(FieldTemplate).where(FieldTemplate.industry_id == industry.id))
    field_keys = loads(template.fields_json, []) if template else []
    fields = extract_fields(ocr_result["text"], field_keys)
    rules = list(
        db.scalars(
            select(AuditRule)
            .options(selectinload(AuditRule.standard))
            .where(AuditRule.industry_id == industry.id, AuditRule.status == "active")
        )
    )
    preliminary_rule_results = evaluate_rules(rules, fields)
    vision_primary = bool(provider and provider.supports_vision and _is_image_file(file.path))
    ocr_result["analysis_mode"] = "vision_primary_ocr_reference" if vision_primary else "ocr_primary"
    model_rule_context = _rules_as_vision_checklist(preliminary_rule_results) if vision_primary else preliminary_rule_results
    model_result = get_model_gateway().analyze(provider, industry.name, ocr_result, fields, model_rule_context, file.path)
    if vision_primary:
        model_result["route"] = "vision+ocr"
        model_result["vision_primary"] = True
    model_fields = model_result.get("extracted_fields")
    if isinstance(model_fields, dict) and model_fields:
        fields = {**fields, **model_fields}
        if model_result.get("recognized_text"):
            ocr_result["text"] = str(model_result["recognized_text"])
        if model_result.get("confidence") is not None:
            ocr_result["average_confidence"] = float(model_result["confidence"])
    rule_results = evaluate_rules(rules, fields)
    _attach_clause_sources(db, rule_results)
    _attach_finding_clause_sources(db, model_result.get("findings", []))
    rule_findings = [
        {
            "title": item["rule_name"],
            "risk_level": item["risk_level"],
            "field_key": item.get("field_key", ""),
            "evidence_text": _stringify(fields.get(item.get("field_key", ""), "")),
            "reason": item["detail"],
            "suggestion": item["suggestion"],
            "standard_code": item.get("standard", ""),
            "standard_clause": item.get("standard_clause", ""),
            "source_excerpt": item.get("source_excerpt", item.get("detail", "")),
        }
        for item in rule_results
        if not item["passed"]
    ]
    existing_titles = {item.get("title") for item in model_result.get("findings", [])}
    model_result["findings"] = [
        *model_result.get("findings", []),
        *[item for item in rule_findings if item["title"] not in existing_titles],
    ]
    if any(item["risk_level"] == "high" for item in model_result["findings"]):
        model_result["risk_level"] = "high"
    elif model_result["findings"]:
        model_result["risk_level"] = "medium"
    needs_review = (
        ocr_result.get("average_confidence", 1) < 0.82
        or model_result.get("risk_level") == "high"
        or any(not item["passed"] and item["risk_level"] == "high" for item in rule_results)
    )
    final_report = {
        "summary": model_result["summary"],
        "risk_level": model_result["risk_level"],
        "route": model_result["route"],
        "vision_primary": bool(model_result.get("vision_primary")),
        "industry": industry.name,
        "industry_code": industry.code,
        "auto_classified_industry": ocr_result.get("auto_classified_industry", ""),
        "standards": sorted({item.get("standard") for item in rule_results if item.get("standard")}),
        "compliant_items": [item for item in rule_results if item["passed"]],
        "findings": [],
        "disclaimer": "AI 结果仅供参考，不构成法律意见或官方检测结论。",
    }

    task.status = ReviewStatus.needs_review.value if needs_review else ReviewStatus.completed.value
    task.ocr_result = dumps(ocr_result)
    task.extracted_fields = dumps(fields)
    task.rule_results = dumps(rule_results)
    task.model_result = dumps(model_result)
    task.final_report = dumps(final_report)
    task.model_used = model_result["provider"]
    task.needs_human_review = needs_review
    task.completed_at = datetime.utcnow()
    recommended_items = recommend_items_for_audit(db, task)
    final_report["recommended_item_codes"] = [item.code for item in recommended_items]
    final_report["findings"] = _normalize_findings(
        model_result["findings"],
        rule_results,
        fields,
        ocr_result,
        final_report["recommended_item_codes"],
        float(ocr_result.get("average_confidence", model_result.get("confidence", 0.75)) or 0.75),
    )
    task.final_report = dumps(final_report)
    db.commit()
    db.refresh(task)
    return serialize_task(task)


def _attach_clause_sources(db: Session, rule_results: list[dict]) -> None:
    if "standard_clauses" not in inspect(db.get_bind()).get_table_names():
        return
    for item in rule_results:
        rule = db.get(AuditRule, item.get("rule_id", ""))
        if not rule or not rule.standard_id:
            continue
        query_text = " ".join(
            str(value)
            for value in [rule.name, rule.field_key, rule.trigger, item.get("detail", ""), item.get("suggestion", "")]
            if value
        )
        tokens = [token for token in query_text.replace("、", " ").replace(",", " ").split() if len(token) >= 2]
        clauses = list(
            db.scalars(
                select(StandardClause)
                .where(StandardClause.standard_id == rule.standard_id, StandardClause.status == "active")
                .order_by(StandardClause.chunk_index)
            )
        )
        if not clauses:
            continue
        best = max(
            clauses,
            key=lambda clause: sum(1 for token in tokens if token in f"{clause.clause_no} {clause.title} {clause.content}"),
        )
        item["standard_clause"] = best.clause_no or item.get("standard_clause", "")
        item["source_excerpt"] = best.content[:500] or best.title or item.get("source_excerpt", "")


def _attach_finding_clause_sources(db: Session, findings: list[dict]) -> None:
    if "standard_clauses" not in inspect(db.get_bind()).get_table_names():
        return
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        standard_code = str(finding.get("standard_code") or finding.get("standard") or "").strip()
        source_excerpt = str(finding.get("source_excerpt") or "").strip()
        if not standard_code or (source_excerpt and source_excerpt not in {"全文", "全文切片"}):
            continue
        clauses = list(
            db.scalars(
                select(StandardClause)
                .where(
                    StandardClause.status == "active",
                    StandardClause.standard.has(code=standard_code),
                )
                .order_by(StandardClause.chunk_index)
            )
        )
        if not clauses:
            continue
        tokens = _finding_source_tokens(finding)
        best = max(clauses, key=lambda clause: sum(1 for token in tokens if token in _compact_clause_text(clause)))
        excerpt = _clean_source_excerpt(best.content or best.title)
        if excerpt:
            finding["standard_clause"] = best.clause_no or finding.get("standard_clause") or ""
            finding["source_excerpt"] = excerpt


def _finding_source_tokens(finding: dict) -> list[str]:
    field_key = str(finding.get("field_key") or "")
    field_tokens = {
        "net_content": ["净含量", "规格"],
        "execution_standard": ["产品标准", "执行标准", "标准代号"],
        "shelf_life": ["生产日期", "保质期", "日期"],
        "manufacturer": ["生产者", "经销者", "名称", "地址", "联系方式"],
        "nutrition": ["营养标签", "核心营养素", "NRV"],
        "license_no": ["生产许可证", "食品生产许可证"],
        "ingredients": ["配料", "原料组成", "添加剂"],
        "target_pet": ["适用宠物", "适用阶段", "犬", "猫"],
        "feeding_instruction": ["饲喂", "喂食", "使用方法"],
        "manual_warning": ["警示", "注意事项", "安全说明"],
        "model_no": ["型号", "规格"],
        "rating": ["额定", "电压", "电流", "功率", "频率"],
        "certification": ["CCC", "认证", "强制性产品认证"],
    }
    text = " ".join(
        str(finding.get(key) or "")
        for key in ["title", "field_key", "reason", "suggestion", "evidence_text"]
    )
    tokens = [*field_tokens.get(field_key, [])]
    tokens.extend(token for token in text.replace("、", " ").replace(",", " ").split() if len(token) >= 2)
    return list(dict.fromkeys(tokens))


def _compact_clause_text(clause: StandardClause) -> str:
    return " ".join(f"{clause.clause_no} {clause.title} {clause.content}".split())


@router.get("/tasks/{task_id}", response_model=AuditTaskRead)
def get_task(task_id: str, db: Session = Depends(get_db)) -> AuditTaskRead:
    task = db.get(AuditTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize_task(task)


@router.patch("/tasks/{task_id}", response_model=AuditTaskRead)
def update_task(task_id: str, payload: AuditTaskUpdate, db: Session = Depends(get_db)) -> AuditTaskRead:
    task = db.get(AuditTask, task_id)
    if not task or task.session_archived:
        raise HTTPException(status_code=404, detail="Task not found")
    task.session_title = payload.session_title.strip()[:160]
    task.session_group = payload.session_group.strip()[:80] or "默认分组"
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.delete("/tasks/{task_id}", response_model=AuditTaskRead)
def delete_task(task_id: str, db: Session = Depends(get_db)) -> AuditTaskRead:
    task = db.get(AuditTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.session_archived = True
    db.commit()
    db.refresh(task)
    return serialize_task(task)
