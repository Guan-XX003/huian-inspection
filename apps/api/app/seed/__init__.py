from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.json_utils import dumps
from app.models import AuditRule, DetectionItem, FieldTemplate, Industry, Lab, ModelProvider, Standard, StandardClause

from .data import SEED_FIELDS, SEED_INDUSTRIES, SEED_ITEMS, SEED_MODELS, SEED_RULES, SEED_STANDARDS
from .official_fulltext import seed_official_fulltext_pack


LEGAL_PACK_DIR = Path(__file__).resolve().parent / "builtin_legal_pack"


def _legal_pack_filename(industry_code: str, standard_code: str) -> str:
    safe_code = "".join(char if char.isalnum() else "_" for char in standard_code).strip("_").lower()
    return f"{industry_code}__{safe_code}.md"


def _write_builtin_legal_file(industry_code: str, standard: dict) -> str:
    LEGAL_PACK_DIR.mkdir(parents=True, exist_ok=True)
    path = LEGAL_PACK_DIR / _legal_pack_filename(industry_code, standard["code"])
    clauses = standard.get("clauses", [])
    lines = [
        f"# {standard['code']} {standard['name']}",
        "",
        f"- 来源类型：内置法规包摘要",
        f"- 适用行业：{industry_code}",
        f"- 版本：{standard.get('version', '现行')}",
        f"- 生效日期：{standard.get('effective_date', '') or '未设置'}",
        "",
        "> 说明：此文件是应用内置的法规/标准审核摘要包，用于本地规则匹配和报告追溯；不等同于官方标准全文。若你拥有授权原文，请在知识库中上传原文件替换或补充。",
        "",
        "## 条款与审核要点",
    ]
    for clause in clauses:
        if isinstance(clause, dict):
            no = str(clause.get("no", "")).strip() or "通用"
            title = str(clause.get("title", "")).strip()
            content = str(clause.get("content", "")).strip()
            lines.append(f"- {no}：{title}")
            if content:
                lines.append(f"  - 摘要：{content}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return str(path)


def _ensure_summary_clauses(db: Session, standard: Standard, clauses: list, source_file: str) -> None:
    if not clauses:
        return
    existing_count = db.scalar(
        select(func.count()).select_from(StandardClause).where(StandardClause.standard_id == standard.id, StandardClause.status == "active")
    ) or 0
    if existing_count:
        return
    for index, clause in enumerate(clauses, 1):
        if not isinstance(clause, dict):
            continue
        no = str(clause.get("no", "")).strip() or "通用"
        title = str(clause.get("title", "")).strip() or standard.name
        content = str(clause.get("content", "")).strip() or title
        db.add(
            StandardClause(
                standard_id=standard.id,
                industry_id=standard.industry_id,
                clause_no=no[:80],
                title=title[:240],
                content=content,
                source_file=source_file,
                chunk_index=index,
                status="active",
            )
        )


def _find_seed_standard(db: Session, industry_id: str, code: str) -> Optional[Standard]:
    return db.scalar(
        select(Standard).where(Standard.industry_id == industry_id, Standard.code == code, Standard.status == "active")
    ) or db.scalar(select(Standard).where(Standard.industry_id == industry_id, Standard.code == code))


def seed_database(db: Session) -> None:
    industries: dict[str, Industry] = {}
    for item in SEED_INDUSTRIES:
        industry = db.scalar(select(Industry).where(Industry.code == item["code"]))
        if industry:
            industry.name = item["name"]
            industry.description = item.get("description", industry.description)
            industry.status = item.get("status", industry.status)
        else:
            industry = Industry(**item)
            db.add(industry)
            db.flush()
        industries[industry.code] = industry

    standards_by_code: dict[tuple[str, str], Standard] = {}
    for industry_code, standards in SEED_STANDARDS.items():
        industry = industries[industry_code]
        for item in standards:
            source_file = item.get("source_file") or _write_builtin_legal_file(industry_code, item)
            standard = _find_seed_standard(db, industry.id, item["code"])
            if standard:
                standard.name = item["name"]
                standard.version = item.get("version", standard.version)
                standard.effective_date = item.get("effective_date", standard.effective_date)
                standard.source_file = source_file
                standard.clauses = dumps(item.get("clauses", []))
                standard.status = "active"
            else:
                standard = Standard(
                    industry_id=industry.id,
                    code=item["code"],
                    name=item["name"],
                    version=item.get("version", "现行"),
                    effective_date=item.get("effective_date", ""),
                    source_file=source_file,
                    clauses=dumps(item.get("clauses", [])),
                )
                db.add(standard)
                db.flush()
            _ensure_summary_clauses(db, standard, item.get("clauses", []), source_file)
            standards_by_code[(industry_code, standard.code)] = standard

    for industry_code, fields in SEED_FIELDS.items():
        template = db.scalar(select(FieldTemplate).where(FieldTemplate.industry_id == industries[industry_code].id))
        if template:
            template.fields_json = dumps(fields)
        else:
            db.add(FieldTemplate(industry_id=industries[industry_code].id, fields_json=dumps(fields)))

    for industry_code, rules in SEED_RULES.items():
        industry = industries[industry_code]
        default_standard = next((value for (code, _), value in standards_by_code.items() if code == industry_code), None)
        for item in rules:
            rule_data = {key: value for key, value in item.items() if key != "standard_code"}
            standard_code = item.get("standard_code")
            standard_ref = (
                standards_by_code.get((industry_code, standard_code))
                if standard_code
                else default_standard
            )
            if standard_code and standard_ref is None:
                standard_ref = _find_seed_standard(db, industry.id, standard_code)
            if standard_code and standard_ref is None:
                source_standard = next(
                    (value for (_, code), value in standards_by_code.items() if code == standard_code),
                    None,
                )
                if source_standard:
                    standard_ref = Standard(
                        industry_id=industry.id,
                        code=source_standard.code,
                        name=source_standard.name,
                        version=source_standard.version,
                        effective_date=source_standard.effective_date,
                        expiry_date=source_standard.expiry_date,
                        source_file=source_standard.source_file,
                        clauses=source_standard.clauses,
                    )
                    db.add(standard_ref)
                    db.flush()
                    standards_by_code[(industry_code, standard_ref.code)] = standard_ref
            rule = db.scalar(
                select(AuditRule).where(AuditRule.industry_id == industry.id, AuditRule.name == item["name"])
            )
            if rule:
                rule.standard_id = standard_ref.id if standard_ref else rule.standard_id
                for key, value in rule_data.items():
                    setattr(rule, key, value)
                rule.status = "active"
            else:
                db.add(
                    AuditRule(
                        industry_id=industry.id,
                        standard_id=standard_ref.id if standard_ref else None,
                        **rule_data,
                    )
                )

    for industry_code, items in SEED_ITEMS.items():
        industry = industries[industry_code]
        for item in items:
            detection_item = db.scalar(
                select(DetectionItem).where(DetectionItem.industry_id == industry.id, DetectionItem.code == item["code"])
            )
            if detection_item:
                for key, value in item.items():
                    setattr(detection_item, key, value)
                detection_item.status = "active"
            else:
                db.add(DetectionItem(industry_id=industry.id, **item))

    seed_official_fulltext_pack(db, industries)

    seed_labs = [
        {"name": "华东食品与宠物食品实验室", "qualification": "CMA/CNAS", "strengths": "食品、乳制品、罐头、速冻、膨化、糖果、宠物食品常规理化、微生物、添加剂、污染物"},
        {"name": "电子电器安规与 EMC 实验室", "qualification": "CMA/CNAS", "strengths": "电子电器安规、EMC、CCC 认证摸底、铭牌和说明书审核"},
        {"name": "综合标签合规审核中心", "qualification": "CMA", "strengths": "食品标签、宠物食品标签、电子铭牌、说明书、法规文件审核"},
    ]
    for legacy_name in ["实验室A", "实验室B"]:
        legacy_lab = db.scalar(select(Lab).where(Lab.name == legacy_name))
        if legacy_lab:
            legacy_lab.status = "inactive"
    for item in seed_labs:
        lab = db.scalar(select(Lab).where(Lab.name == item["name"]))
        if lab:
            lab.qualification = item["qualification"]
            lab.strengths = item["strengths"]
            lab.status = "active"
        else:
            db.add(Lab(**item))

    if (db.scalar(select(func.count()).select_from(ModelProvider)) or 0) == 0:
        for item in SEED_MODELS:
            db.add(ModelProvider(**item))

    db.commit()
