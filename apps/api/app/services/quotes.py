from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.json_utils import dumps, loads
from app.models import AuditTask, DetectionItem, Lab, Quote


def make_quote_no() -> str:
    return f"Q{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


def build_quote_from_items(
    db: Session,
    detection_item_ids: list[str],
    customer_name: str = "",
    audit_task_id: Optional[str] = None,
    discount_rate: float = 1,
    tax_rate: float = 0.06,
) -> Quote:
    if not detection_item_ids:
        raise ValueError("No detection items selected")
    items = list(db.scalars(select(DetectionItem).where(DetectionItem.id.in_(detection_item_ids))))
    if not items:
        raise ValueError("No active detection items found")
    labs = list(db.scalars(select(Lab).where(Lab.status == "active")))
    quote_items = []
    for item in items:
        lab = _match_lab(labs, item)
        quote_items.append(
            {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "method_standard": item.method_standard,
            "judgment_standard": item.judgment_standard,
            "price": item.price,
            "cycle_days": item.cycle_days,
            "sample_amount": item.sample_amount,
            "package_name": item.package_name,
            "lab_name": lab.name if lab else "待分配实验室",
            "lab_qualification": lab.qualification if lab else "",
            "lab_strengths": lab.strengths if lab else "",
            "service_note": _service_note(item),
        }
        )
    subtotal = sum(item["price"] for item in quote_items)
    total = round(subtotal * discount_rate * (1 + tax_rate), 2)
    quote = Quote(
        quote_no=make_quote_no(),
        audit_task_id=audit_task_id,
        customer_name=customer_name,
        items_json=dumps(quote_items),
        subtotal=subtotal,
        tax_rate=tax_rate,
        discount_rate=discount_rate,
        total=total,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


def _match_lab(labs: list[Lab], item: DetectionItem) -> Optional[Lab]:
    if not labs:
        return None
    haystack = f"{item.name} {item.method_standard} {item.package_name}"
    scored: list[tuple[int, Lab]] = []
    for lab in labs:
        score = 0
        strengths = lab.strengths or ""
        if any(word in haystack for word in ["电子", "电器", "EMC", "安规", "4943", "9254"]):
            score += 6 if any(word in strengths for word in ["电子", "电器", "安规", "EMC", "认证"]) else 0
        if any(word in haystack for word in ["宠物", "犬", "猫"]):
            score += 5 if "宠物" in strengths else 0
        if any(word in haystack for word in ["食品", "标签", "营养", "微生物", "添加剂", "污染物", "罐头", "速冻", "膨化", "糖果", "乳"]):
            score += 5 if "食品" in strengths else 0
        if "CNAS" in lab.qualification:
            score += 1
        scored.append((score, lab))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


def _service_note(item: DetectionItem) -> str:
    if any(word in item.name for word in ["标签", "审核", "铭牌", "说明书"]):
        return "资料审核项目，可用图片/PDF/包装文件作为样品资料。"
    if any(word in item.name for word in ["微生物", "商业无菌"]):
        return "建议按独立包装送样，注意冷链和样品完整性。"
    if any(word in item.name for word in ["EMC", "安规"]):
        return "需提供整机、适配器、说明书和关键配件。"
    return "按报价库样品要求送样，必要时由实验室复核。"


def _is_usable_quote_item(item: DetectionItem) -> bool:
    if item.price <= 0:
        return False
    if item.price < 50 and "需人工确认" in (item.sample_amount or ""):
        return False
    if any(token in item.name for token in ["价格 周期", "周期个工作日", "需人工确认"]):
        return False
    return True


def recommend_items_for_audit(db: Session, audit_task: AuditTask) -> list[DetectionItem]:
    all_items = list(
        db.scalars(
            select(DetectionItem).where(
                DetectionItem.industry_id == audit_task.industry_id,
                DetectionItem.status == "active",
            )
        )
    )
    all_items = [item for item in all_items if _is_usable_quote_item(item)]
    if not all_items:
        return []

    final_report = loads(audit_task.final_report, {})
    findings = final_report.get("findings", []) if isinstance(final_report, dict) else []
    rule_results = loads(audit_task.rule_results, [])
    extracted_fields = loads(audit_task.extracted_fields, {})
    signals = " ".join(
        [
            audit_task.document_type or "",
            " ".join(str(value) for value in extracted_fields.values()),
            " ".join(
                f"{item.get('title', '')} {item.get('reason', '')} {item.get('suggestion', '')}"
                for item in findings
                if isinstance(item, dict)
            ),
            " ".join(
                f"{item.get('rule_name', '')} {item.get('field_key', '')} {item.get('detail', '')} {item.get('standard', '')}"
                for item in rule_results
                if isinstance(item, dict)
            ),
        ]
    )

    scored: list[tuple[int, DetectionItem]] = []
    for item in all_items:
        haystack = f"{item.name} {item.method_standard} {item.judgment_standard} {item.package_name}"
        score = 0
        if any(word in signals for word in ["标签", "宣传", "claims", "许可证", "license"]):
            score += 4 if any(word in haystack for word in ["标签", "审核", "7718", "28050"]) else 0
        if any(word in signals for word in ["营养", "nutrition", "NRV", "蛋白质", "脂肪", "钠"]):
            score += 5 if any(word in haystack for word in ["营养", "5009", "28050"]) else 0
        if any(word in signals for word in ["乳", "发酵乳", "灭菌乳", "非脂乳固体"]):
            score += 5 if any(word in haystack for word in ["乳", "蛋白质", "脂肪", "微生物"]) else 0
        if any(word in signals for word in ["罐头", "商业无菌", "常温"]):
            score += 6 if any(word in haystack for word in ["罐头", "商业无菌", "7098", "4789.26"]) else 0
        if any(word in signals for word in ["速冻", "冷冻", "-18", "微生物"]):
            score += 5 if any(word in haystack for word in ["速冻", "微生物", "19295", "4789"]) else 0
        if any(word in signals for word in ["膨化", "薯片", "锅巴", "酸价", "过氧化值", "油脂"]):
            score += 5 if any(word in haystack for word in ["膨化", "酸价", "过氧化", "17401"]) else 0
        if any(word in signals for word in ["糖果", "甜味剂", "色素", "防腐剂", "糖醇"]):
            score += 5 if any(word in haystack for word in ["糖果", "甜味剂", "色素", "防腐剂", "添加剂", "2760"]) else 0
        if any(word in signals for word in ["重金属", "污染物", "铅", "镉", "砷", "汞"]):
            score += 5 if any(word in haystack for word in ["重金属", "污染物", "5009", "2762"]) else 0
        if any(word in signals for word in ["宠物", "犬", "猫", "粗蛋白", "粗脂肪", "成分分析"]):
            score += 5 if any(word in haystack for word in ["宠物", "粗蛋白", "粗脂肪", "卫生指标"]) else 0
        if any(word in signals for word in ["电器", "铭牌", "额定", "CCC", "安规"]):
            score += 5 if any(word in haystack for word in ["铭牌", "说明书", "安规", "4943"]) else 0
        if any(word in signals for word in ["EMC", "电磁兼容", "发射", "骚扰"]):
            score += 5 if any(word in haystack for word in ["EMC", "9254", "电磁兼容"]) else 0
        if score > 0:
            scored.append((score, item))

    if scored:
        return [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)[:5]]

    label_items = [item for item in all_items if any(word in item.name for word in ["标签", "审核", "铭牌", "说明书"])]
    return (label_items or all_items)[:3]
