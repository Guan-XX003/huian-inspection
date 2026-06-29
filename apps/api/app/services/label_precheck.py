import re
from typing import Any


FIELD_LABELS = {
    "product_name": "产品名称",
    "product_type": "产品类别",
    "ingredients": "配料表",
    "additives": "添加剂/营养添加剂",
    "nutrition": "营养成分表/成分分析保证值",
    "net_content": "净含量/规格",
    "license_no": "生产许可证号",
    "manufacturer": "生产者/制造商",
    "address": "地址",
    "phone": "联系方式",
    "shelf_life": "保质期",
    "production_date": "生产日期",
    "expiry_date": "到期日期",
    "claims": "宣传语/功效宣称",
    "storage_condition": "贮存条件",
    "execution_standard": "执行标准",
    "target_pet": "适用宠物/阶段",
    "feeding_instruction": "饲喂说明",
    "manual_warning": "警示语/注意事项",
    "model_no": "型号",
    "rating": "额定参数",
    "certification": "认证标识",
}

SECTION_PATTERNS = {
    "product_name": [r"(?:产品名称|品名|商品名称)[:：]?\s*([^\n]{2,80})"],
    "ingredients": [r"(?:配料表?|原料组成|主要原料)[:：]\s*([\s\S]{0,420})"],
    "nutrition": [r"(?:营养成分表|营养标签|成分分析保证值|保证分析值)[:：]?\s*([\s\S]{0,520})"],
    "net_content": [r"(?:净含量|规格)[:：]?\s*([^\n]{1,80})"],
    "license_no": [r"(SC\s*\d{14})", r"(?:许可证编号|食品生产许可证编号)[:：]?\s*([A-Z0-9]{8,24})"],
    "manufacturer": [r"(?:生产者|生产商|制造商|委托方|受委托方|经销商)[:：]\s*([^\n]{2,120})"],
    "address": [r"(?:生产地址|地址|注册地址)[:：]\s*([^\n]{4,160})"],
    "phone": [r"(?:电话|联系电话|联系方式|服务热线|客服热线)[:：]\s*([0-9\-— ]{6,40})"],
    "shelf_life": [r"(?:保质期|质保期|有效期)[:：]\s*([^\n]{1,80})"],
    "production_date": [r"(?:生产日期(?:\s*/\s*保质期到期日)?|制造日期|喷码日期)[:：]\s*([^\n]{1,100})"],
    "expiry_date": [r"(?:到期日期|有效期至|保质期至)[:：]\s*([^\n]{1,80})"],
    "storage_condition": [r"(?:贮存条件|储存条件|保存条件)[:：]\s*([^\n]{2,140})"],
    "execution_standard": [r"(?:执行标准|产品标准|标准号|放行标准)[:：]?\s*([A-Z0-9/.\-\s]+)"],
    "claims": [r"(?:宣传语|产品特点|卖点)[:：]\s*([^\n]{2,180})"],
    "target_pet": [r"(?:适用(?:对象|宠物|阶段)|适用犬种|适用猫种)[:：]\s*([^\n]{1,120})"],
    "feeding_instruction": [r"(?:饲喂方法|喂食指南|喂养建议|建议喂食量|使用方法|饲喂说明)[:：]\s*([\s\S]{0,360})"],
    "manual_warning": [r"(?:警示语|安全警示|注意事项|警告)[:：]\s*([\s\S]{0,260})"],
    "model_no": [r"(?:型号|规格型号)[:：]\s*([^\n]{1,80})"],
    "rating": [r"(?:额定输入|额定输出|额定参数|额定电压|额定功率)[:：]\s*([^\n]{1,120})"],
    "certification": [r"(?:CCC|CQC|认证|证书编号|认证编号)[:：]?\s*([^\n]{1,120})"],
}

REQUIRED_BY_INDUSTRY = {
    "food": ["product_name", "ingredients", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "storage_condition", "execution_standard"],
    "dairy": ["product_name", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "storage_condition", "execution_standard"],
    "canned_food": ["product_name", "ingredients", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "storage_condition", "execution_standard"],
    "frozen_food": ["product_name", "ingredients", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "storage_condition", "execution_standard"],
    "puffed_food": ["product_name", "ingredients", "nutrition", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "storage_condition", "execution_standard"],
    "candy": ["product_name", "ingredients", "net_content", "license_no", "manufacturer", "address", "shelf_life", "production_date", "storage_condition", "execution_standard"],
    "pet_food": ["product_name", "ingredients", "nutrition", "target_pet", "net_content", "manufacturer", "address", "shelf_life", "storage_condition", "feeding_instruction"],
    "electronics": ["product_name", "model_no", "rating", "certification", "manufacturer", "address", "execution_standard", "manual_warning"],
}


def build_label_precheck(ocr_result: dict[str, Any], fields: dict[str, Any], field_keys: list[str], industry_code: str) -> dict[str, Any]:
    text = _normalize_text(str(ocr_result.get("text", "")))
    blocks = ocr_result.get("blocks", [])
    section_map = _build_section_map(text, blocks if isinstance(blocks, list) else [])
    merged_fields = dict(fields)
    field_confidence: dict[str, float] = {}
    sections = []

    for key in field_keys:
        current = str(merged_fields.get(key) or "").strip()
        section = section_map.get(key, {})
        section_text = str(section.get("text") or "").strip()
        if not current and section_text:
            merged_fields[key] = section_text
            current = section_text
        confidence = _field_confidence(key, current, section, float(ocr_result.get("average_confidence", 0) or 0))
        field_confidence[key] = confidence
        sections.append(
            {
                "field_key": key,
                "label": FIELD_LABELS.get(key, key),
                "text": current,
                "present": bool(current),
                "confidence": confidence,
                "source": section.get("source", "ocr_text" if current else "missing"),
                "position": section.get("position", ""),
            }
        )

    model_sections = ocr_result.get("model_label_sections", [])
    if isinstance(model_sections, list):
        sections, merged_fields, field_confidence = _merge_model_sections(sections, merged_fields, field_confidence, model_sections)

    required_keys = [key for key in REQUIRED_BY_INDUSTRY.get(industry_code, field_keys) if key in field_keys]
    missing = [key for key in required_keys if not str(merged_fields.get(key) or "").strip()]
    low_confidence = [
        key
        for key in required_keys
        if str(merged_fields.get(key) or "").strip() and field_confidence.get(key, 0) < 0.72
    ]
    unreadable_parts = list(dict.fromkeys([*ocr_result.get("unreadable_parts", []), *[FIELD_LABELS.get(key, key) for key in low_confidence]]))
    completeness_score = round((len(required_keys) - len(missing)) / max(len(required_keys), 1), 2)
    recognition_score = round(
        completeness_score * 0.55
        + min(float(ocr_result.get("average_confidence", 0) or 0), 1) * 0.25
        + (1 - min(len(low_confidence) / max(len(required_keys), 1), 1)) * 0.2,
        2,
    )
    return {
        "fields": merged_fields,
        "sections": sections,
        "required_fields": required_keys,
        "missing_fields": missing,
        "low_confidence_fields": low_confidence,
        "unreadable_parts": unreadable_parts,
        "completeness_score": completeness_score,
        "recognition_score": recognition_score,
        "summary": _summary(required_keys, missing, low_confidence, recognition_score),
    }


def _merge_model_sections(
    sections: list[dict[str, Any]],
    fields: dict[str, Any],
    confidence: dict[str, float],
    model_sections: list[Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, float]]:
    by_key = {section.get("field_key"): section for section in sections}
    for section in model_sections:
        if not isinstance(section, dict):
            continue
        key = str(section.get("field_key") or "").strip()
        if not key:
            continue
        text = str(section.get("text") or "").strip()
        try:
            section_confidence = float(section.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            section_confidence = 0
        section_confidence = round(max(0, min(section_confidence, 1)), 2)
        existing = by_key.get(key)
        if text and (not fields.get(key) or section_confidence >= confidence.get(key, 0)):
            fields[key] = text
            confidence[key] = max(section_confidence, confidence.get(key, 0))
        if existing:
            if text and (not existing.get("text") or section_confidence >= float(existing.get("confidence", 0) or 0)):
                existing.update(
                    {
                        "text": text,
                        "present": bool(text),
                        "confidence": max(section_confidence, float(existing.get("confidence", 0) or 0)),
                        "source": "vision_model",
                        "note": section.get("note", ""),
                    }
                )
        else:
            next_section = {
                "field_key": key,
                "label": str(section.get("label") or FIELD_LABELS.get(key, key)),
                "text": text,
                "present": bool(text),
                "confidence": section_confidence,
                "source": "vision_model",
                "position": "",
                "note": section.get("note", ""),
            }
            sections.append(next_section)
            by_key[key] = next_section
    return sections, fields, confidence


def precheck_findings(precheck: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for index, key in enumerate(precheck.get("missing_fields", []), start=1):
        label = FIELD_LABELS.get(key, key)
        findings.append(
            {
                "finding_id": f"P-MISS-{index:02d}",
                "title": f"{label}缺失或未识别",
                "risk_level": "medium",
                "field_key": key,
                "evidence_text": "",
                "reason": f"识别预审未能从标签中确认“{label}”。该字段可能确实缺失，也可能因图片清晰度、遮挡或排版导致未识别。",
                "suggestion": f"请补充/拍清“{label}”区域，或人工核对原包装后再出具结论。",
                "standard_code": "",
                "standard_clause": "",
                "source_excerpt": "识别预审层根据标签结构化字段完整性生成。",
                "confidence": 0.68,
                "needs_human_review": True,
            }
        )
    offset = len(findings)
    for index, key in enumerate(precheck.get("low_confidence_fields", []), start=1):
        label = FIELD_LABELS.get(key, key)
        text = _section_text(precheck, key)
        findings.append(
            {
                "finding_id": f"P-LOW-{index:02d}",
                "title": f"{label}识别置信度偏低",
                "risk_level": "low",
                "field_key": key,
                "evidence_text": text,
                "reason": f"识别预审已提取“{label}”，但置信度偏低，后续法规判断可能受影响。",
                "suggestion": "建议人工复核该区域文字；如图片模糊，请重新上传更清晰的标签局部图。",
                "standard_code": "",
                "standard_clause": "",
                "source_excerpt": "识别预审层根据 OCR/视觉文本质量生成。",
                "confidence": 0.72,
                "needs_human_review": True,
            }
        )
    for number, finding in enumerate(findings, start=1):
        finding["finding_id"] = finding.get("finding_id") or f"P-{offset + number:03d}"
    return findings


def _build_section_map(text: str, blocks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    section_map: dict[str, dict[str, Any]] = {}
    for key, patterns in SECTION_PATTERNS.items():
        value = ""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = _clean_section(match.group(1))
                break
        if not value:
            value = _line_window_for_key(text, key)
        if value:
            section_map[key] = {"text": value, "source": "regex_section", "position": _nearest_position(blocks, value)}
    return section_map


def _line_window_for_key(text: str, key: str) -> str:
    keywords = {
        "ingredients": ["配料", "原料"],
        "nutrition": ["营养成分", "成分分析", "能量", "蛋白质", "脂肪", "钠"],
        "claims": ["无添加", "精选", "健康", "营养", "推荐", "功效", "治疗", "最好", "第一"],
        "storage_condition": ["贮存", "储存", "保存"],
        "manufacturer": ["生产", "制造", "委托", "经销"],
        "address": ["地址"],
    }.get(key, [])
    if not keywords:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if any(keyword in line for keyword in keywords):
            return _clean_section("\n".join(lines[index : index + 4]))
    return ""


def _field_confidence(key: str, value: str, section: dict[str, Any], average_confidence: float) -> float:
    if not value:
        return 0
    if key == "ingredients" and value.strip(" ：:;；,，") in {"配料", "配料表", "原料", "原料组成"}:
        return 0.38
    score = max(min(average_confidence or 0.76, 0.98), 0.45)
    if section.get("source") == "regex_section":
        score += 0.08
    if key == "license_no" and re.fullmatch(r"SC\d{14}", value.replace(" ", "")):
        score = max(score, 0.95)
    if key == "net_content" and re.search(r"\d", value) and re.search(r"(g|kg|ml|mL|L|克|千克|升)", value):
        score = max(score, 0.9)
    if key == "nutrition" and any(word in value for word in ["能量", "蛋白质", "脂肪", "钠", "粗蛋白", "粗脂肪"]):
        score = max(score, 0.86)
    if any(marker in value for marker in ["?", "�", "口口"]) or len(value) <= 1:
        score -= 0.22
    return round(max(0.35, min(score, 0.99)), 2)


def _nearest_position(blocks: list[dict[str, Any]], value: str) -> Any:
    compact_value = _compact(value)
    for block in blocks:
        text = str(block.get("text") or "")
        if _compact(text) and (_compact(text) in compact_value or compact_value[:18] in _compact(text)):
            return block.get("position", "")
    return ""


def _section_text(precheck: dict[str, Any], key: str) -> str:
    for section in precheck.get("sections", []):
        if section.get("field_key") == key:
            return str(section.get("text") or "")
    return ""


def _summary(required: list[str], missing: list[str], low_confidence: list[str], score: float) -> str:
    if not required:
        return "已完成标签结构化识别预审。"
    if missing:
        names = "、".join(FIELD_LABELS.get(key, key) for key in missing[:6])
        return f"标签结构化识别完成度 {score:.0%}，未确认字段：{names}。"
    if low_confidence:
        names = "、".join(FIELD_LABELS.get(key, key) for key in low_confidence[:6])
        return f"标签字段基本齐全，{names} 需要人工复核。"
    return "标签主要字段已完成结构化识别，未发现明显缺失字段。"


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    replacements = {
        "放行标准": "执行标准",
        "本行标港": "执行标准",
        "执行标港": "执行标准",
        "OIAFD": "Q/AFD",
        "O/AFD": "Q/AFD",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _clean_section(value: str) -> str:
    value = re.split(r"\n\s*(?:产品名称|配料|净含量|生产者|地址|保质期|贮存|执行标准|营养成分表)[:：]", value.strip())[0]
    lines = [line.strip(" ：:;；,，") for line in value.splitlines() if line.strip()]
    return "\n".join(lines[:8])[:700]


def _compact(value: str) -> str:
    return re.sub(r"\W+", "", value.lower())
