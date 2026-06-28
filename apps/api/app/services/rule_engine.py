import re
from typing import Any

from app.json_utils import loads
from app.models import AuditRule


FIELD_ALIASES = {
    "manufacturer": ["manufacturer", "address", "contact", "phone", "service_phone"],
    "shelf_life": ["shelf_life", "production_date", "expiry_date", "storage_condition"],
}


def _field_value(fields: dict[str, Any], field_key: str) -> str:
    keys = FIELD_ALIASES.get(field_key, [field_key])
    return "\n".join(str(fields.get(key, "")) for key in keys if fields.get(key))


def _best_clause(rule: AuditRule) -> tuple[str, str]:
    if not rule.standard:
        return "", ""
    clauses = loads(rule.standard.clauses, [])
    if not isinstance(clauses, list) or not clauses:
        return "", rule.standard.name

    keywords = [
        rule.name,
        rule.field_key,
        rule.trigger,
        rule.suggestion,
    ]
    keyword_text = " ".join(item for item in keywords if item)
    best = clauses[0]
    for clause in clauses:
        if not isinstance(clause, dict):
            continue
        clause_text = f"{clause.get('no', '')} {clause.get('title', '')}"
        if any(token and token in clause_text for token in re.split(r"[、,/，\s]+", keyword_text)):
            best = clause
            break
    return str(best.get("no", "")), str(best.get("title", rule.standard.name))


def _required_terms(rule: AuditRule) -> list[str]:
    if rule.trigger and any(separator in rule.trigger for separator in ["、", "/"]):
        return [item.strip() for item in re.split(r"[、/,，]", rule.trigger) if item.strip()]
    if rule.field_key == "nutrition":
        return ["能量", "蛋白质", "脂肪", "碳水化合物", "钠"]
    return []


def evaluate_rules(rules: list[AuditRule], fields: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for rule in rules:
        value = _field_value(fields, rule.field_key)
        passed = True
        detail = "已通过基础校验"

        if rule.rule_type == "deterministic":
            if rule.field_key == "license_no":
                passed = bool(re.fullmatch(r"SC\d{14}", value))
                detail = "食品生产许可证编号格式正确" if passed else "未识别到有效 SC 编号"
            elif rule.field_key == "nutrition":
                required = _required_terms(rule)
                missing = [item for item in required if item not in value]
                passed = not missing
                if any(item.startswith("粗") or item in {"水分", "钙", "磷"} for item in required):
                    detail = "成分分析保证值基础项完整" if passed else f"缺少：{'、'.join(missing)}"
                else:
                    detail = "营养成分表基础项完整" if passed else f"缺少：{'、'.join(missing)}"
            elif rule.field_key == "net_content":
                passed = bool(value) and bool(re.search(r"\d", value)) and any(unit in value for unit in ["g", "kg", "mL", "ml", "L", "升", "克", "千克"])
                detail = "净含量已识别并包含计量单位" if passed else "净含量缺失或未识别到规范计量单位"
            elif rule.field_key == "storage_condition":
                strict_cold_chain = any(keyword in rule.trigger for keyword in ["-18", "冷冻", "速冻"])
                keywords = ["冷冻", "冷藏", "-18", "18℃", "阴凉", "干燥", "通风", "避光", "常温", "密封", "保存", "贮存", "储存"]
                passed = bool(value) and any(keyword in value for keyword in keywords)
                if strict_cold_chain:
                    passed = bool(value) and any(keyword in value for keyword in ["冷冻", "-18", "18℃", "速冻"])
                detail = "贮存条件已识别" if passed else "未识别到明确贮存条件"
            elif rule.field_key == "manufacturer":
                passed = bool(fields.get("manufacturer")) and (bool(fields.get("address")) or bool(fields.get("contact")) or bool(fields.get("phone")) or bool(fields.get("service_phone")))
                detail = "生产者名称及地址/联系方式已识别" if passed else "生产者名称、地址或联系方式缺失"
            elif rule.field_key == "shelf_life":
                passed = bool(fields.get("shelf_life")) and (bool(fields.get("production_date")) or bool(fields.get("expiry_date")))
                detail = "日期和保质期信息已识别" if passed else "生产日期、到期日期或保质期信息缺失"
            elif rule.trigger and any(separator in rule.trigger for separator in ["、", "/"]):
                required = _required_terms(rule)
                hits = [item for item in required if item in value]
                passed = bool(value) and bool(hits)
                detail = f"字段已识别：{'、'.join(hits)}" if passed else f"字段缺失或未命中建议内容：{'、'.join(required[:6])}"
            else:
                passed = bool(value)
                detail = "字段已识别" if passed else "字段缺失或 OCR 未识别"
        elif rule.rule_type == "ai":
            risky_words = [word.strip() for word in rule.trigger.replace("、", ",").split(",") if word.strip()]
            hits = [word for word in risky_words if word and word in value]
            passed = not hits
            detail = "未发现明显高风险宣传语" if passed else f"疑似触发：{'、'.join(hits)}"

        standard_clause, source_excerpt = _best_clause(rule)
        results.append(
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "field_key": rule.field_key,
                "passed": passed,
                "risk_level": "low" if passed else rule.risk_level,
                "detail": detail,
                "suggestion": "" if passed else rule.suggestion,
                "standard": rule.standard.code if rule.standard else "",
                "standard_clause": standard_clause,
                "source_excerpt": source_excerpt,
            }
        )
    return results
