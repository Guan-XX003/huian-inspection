import re


def extract_fields(ocr_text: str, field_keys: list[str]) -> dict:
    fields: dict[str, str] = {}
    normalized_text = _normalize_ocr_text(ocr_text)
    patterns = {
        "product_name": r"(?:产品名称|品名|商品名称|芒品名術|芒品名称)[:：]\s*(.+)",
        "product_type": r"(?:产品类型|食品类别|类别)[:：]\s*(.+)",
        "ingredients": r"(?:配料|原料组成|主要原料|原辅料)[:：]\s*(.+)",
        "additives": r"(?:添加剂组成|添加剂|营养性添加剂|微量元素|技术添加剂)[:：]\s*(.+)",
        "nutrition": r"(?:营养成分表|营养标签|成分分析保证值|产品成分分析保证值|保证分析值)[:：]\s*(.+)",
        "net_content": r"净含量[:：]\s*(.+)",
        "license_no": r"(?:食品生产许可证编号|许可证编号)[:：]\s*(SC\d{14})",
        "manufacturer": r"(?:生产商|生产者|制造商|委托方|受委托方|经销商|运营商)[:：]\s*(.+)",
        "address": r"(?:地址|生产地址|制造商地址|注册地址|地\s*址)[:：]\s*(.+)",
        "phone": r"(?:电话|联系电话|联系方式|客服热线|服务热线)[:：]\s*(.+)",
        "shelf_life": r"(?:保质期|质保期|有效期)[:：]\s*(.+)",
        "production_date": r"(?:生产日期(?:\s*/\s*保质期到期日)?|制造日期|生产批号|喷码日期)[:：]\s*(.+)",
        "expiry_date": r"(?:到期日期|失效日期|有效期至|保质期至)[:：]\s*(.+)",
        "execution_standard": r"(?:执行标准|产品标准|标准号|本行标港|执行标港|放行标准)[:：]\s*([A-Z0-9/.\-\s]+)",
        "claims": r"宣传语[:：]\s*(.+)",
        "storage_condition": r"(?:贮存条件|储存条件|保存条件)[:：]\s*(.+)",
        "target_pet": r"(?:适用(?:对象|宠物|阶段)|适用犬种|适用猫种)[:：]\s*(.+)",
        "feeding_instruction": r"(?:饲喂方法|喂食指南|喂养建议|建议喂食量|使用方法|饲喂说明)[:：]\s*(.+)",
        "model_no": r"型号[:：]\s*(.+)",
        "rating": r"(?:额定输入|额定输出|额定参数|额定电压|额定功率)[:：]\s*(.+)",
        "certification": r"(?:认证|CCC|CQC|证书编号|认证编号|强制性产品认证)[:：]\s*(.+)",
        "manual_warning": r"(?:警示语|安全警示|注意事项|警告)[:：]\s*(.+)",
    }

    for key in field_keys:
        pattern = patterns.get(key)
        if not pattern:
            fields[key] = ""
            continue
        match = re.search(pattern, normalized_text)
        fields[key] = _clean_value(match.group(1)) if match else ""

    _fill_food_fallbacks(fields, normalized_text)
    return fields


def _normalize_ocr_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    replacements = {
        "芒品名術": "产品名称",
        "芒品名称": "产品名称",
        "周味": "调味",
        "本行标港": "执行标准",
        "执行标港": "执行标准",
        "放行标准": "执行标准",
        "食品生产许可证编品": "食品生产许可证编号",
        "晋砂糖": "白砂糖",
        "父再水": "饮用水",
        "OIAFD": "Q/AFD",
        "O/AFD": "Q/AFD",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"地\s*\n\s*址[:：]", "地址：", normalized)
    return normalized


def _clean_value(value: str) -> str:
    return re.split(r"\n", value.strip())[0].strip(" ：:;；,，")


def _fill_food_fallbacks(fields: dict[str, str], text: str) -> None:
    if not fields.get("claims"):
        claim_keywords = [
            "国家级",
            "最高级",
            "最佳",
            "最优",
            "最好",
            "第一",
            "唯一",
            "100%",
            "百分百",
            "根治",
            "治愈",
            "治疗",
            "预防疾病",
            "抗癌",
            "降血糖",
            "降血压",
            "无副作用",
            "保证有效",
            "增强免疫",
            "替代药物",
            "药用",
            "处方",
            "临床证明",
            "权威推荐",
            "销量第一",
        ]
        hit_lines = []
        for line in text.splitlines():
            clean_line = line.strip()
            if clean_line and any(keyword in clean_line for keyword in claim_keywords):
                hit_lines.append(clean_line[:120])
        if hit_lines:
            fields["claims"] = "；".join(hit_lines[:8])
    if not fields.get("license_no"):
        match = re.search(r"SC\d{14}", text)
        if match:
            fields["license_no"] = match.group(0)
    if not fields.get("execution_standard"):
        match = re.search(r"Q/[A-Z0-9]+\s*\d{4,}[A-Z]?", text)
        if match:
            fields["execution_standard"] = _normalize_standard_code(match.group(0))
    if fields.get("execution_standard"):
        fields["execution_standard"] = _normalize_standard_code(fields["execution_standard"])
    if fields.get("production_date") and any(marker in fields["production_date"] for marker in ["见包装喷码", "见喷码"]):
        date_matches = re.findall(r"20\d{2}[/.\-]\d{1,2}[/.\-]\d{1,2}", text)
        if date_matches:
            fields["production_date"] = f"{fields['production_date']}；喷码：{date_matches[0]}"
            if len(date_matches) > 1 and not fields.get("expiry_date"):
                fields["expiry_date"] = date_matches[1]
    if not _has_meaningful_ingredients(fields.get("ingredients", "")):
        ingredients = _collect_ingredient_lines(text)
        if ingredients:
            fields["ingredients"] = ingredients
    if not fields.get("product_name"):
        match = re.search(r"([\u4e00-\u9fa5]{1,12}凉粉[^\n]*)", text)
        if match:
            fields["product_name"] = _clean_value(match.group(1))
    if not fields.get("nutrition") and "营养成分表" in text:
        required = ["能量", "蛋白质", "脂肪", "碳水化合物", "钠"]
        hits = [item for item in required if item in text]
        if hits:
            fields["nutrition"] = "、".join(hits)
    if not fields.get("nutrition") and any(keyword in text for keyword in ["成分分析保证值", "保证分析值", "粗蛋白", "粗脂肪"]):
        pet_required = ["粗蛋白", "粗脂肪", "粗纤维", "粗灰分", "水分", "钙", "磷", "牛磺酸"]
        hits = [item for item in pet_required if item in text]
        if hits:
            fields["nutrition"] = "、".join(hits)
    if not fields.get("target_pet"):
        pet_hits = [item for item in ["犬", "猫", "幼犬", "幼猫", "成年犬", "成年猫", "全阶段"] if item in text]
        if pet_hits:
            fields["target_pet"] = "、".join(dict.fromkeys(pet_hits))
    if not fields.get("feeding_instruction") and any(keyword in text for keyword in ["饲喂", "喂食", "喂养", "建议喂食量"]):
        fields["feeding_instruction"] = "已识别到饲喂或喂食说明"


def _normalize_standard_code(value: str) -> str:
    normalized = value.strip().replace(" ", "")
    normalized = normalized.replace("OIAFD", "Q/AFD").replace("O/AFD", "Q/AFD")
    normalized = normalized.replace("00015", "0001S")
    return normalized


def _has_meaningful_ingredients(value: str) -> bool:
    normalized = value.strip(" ：:;；,，")
    return len(normalized) > 8 and normalized not in {"配料", "配料表", "原料", "原料组成"}


def _collect_ingredient_lines(text: str) -> str:
    ingredient_markers = [
        "饮用水",
        "淀粉",
        "食用盐",
        "白砂糖",
        "植物油",
        "辣椒",
        "香辛料",
        "食品添加剂",
        "谷氨酸钠",
        "呈味核苷酸",
        "调味",
        "致敏物质",
        "大豆",
        "芝麻",
    ]
    stop_markers = ["营养成分", "执行标准", "生产商", "运营商", "地址", "许可证", "保质期", "贮存条件", "温馨提示"]
    lines = [line.strip(" ：:;；,，") for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    recent_ingredient_line = False
    for line in lines:
        compact_line = re.sub(r"\s+", "", line)
        if any(stop in compact_line for stop in stop_markers):
            recent_ingredient_line = False
            continue
        has_marker = any(marker in line for marker in ingredient_markers)
        starts_like_pack = re.match(r"^(?:调味|酱|水|料)?包[:：]", line) is not None
        likely_continuation = recent_ingredient_line and len(line) >= 3 and any(char in line for char in "、，,（）()")
        if has_marker or starts_like_pack or ("配料" in line and len(line) > 4):
            selected.append(line)
            recent_ingredient_line = True
        elif likely_continuation:
            selected.append(line)
            recent_ingredient_line = True
        else:
            recent_ingredient_line = False
        if len(selected) >= 10:
            break
    cleaned = [line for line in selected if line not in {"配料", "原料"}]
    return "；".join(cleaned[:8])[:600]
