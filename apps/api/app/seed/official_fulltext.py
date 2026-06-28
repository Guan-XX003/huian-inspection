from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.json_utils import dumps, loads
from app.models import Standard, StandardClause
from app.services.clause_chunker import chunk_standard_text
from app.services.document_parser import get_document_parser


OFFICIAL_FULLTEXT_DIR = Path(__file__).resolve().parent / "builtin_official_pack"


OFFICIAL_FULLTEXT_PACK: list[dict[str, Any]] = [
    {
        "industry_code": "food",
        "code": "GB 7718-2011",
        "name": "食品安全国家标准 预包装食品标签通则",
        "version": "2011",
        "effective_date": "2012-04-20",
        "filename": "gb_7718_2011_nhc.pdf",
        "source": "国家卫生健康委员会公开文件",
    },
    {
        "industry_code": "food",
        "code": "GB 28050-2011",
        "name": "食品安全国家标准 预包装食品营养标签通则",
        "version": "2011",
        "effective_date": "2013-01-01",
        "filename": "gb_28050_2011_nhc.pdf",
        "source": "国家卫生健康委员会公开文件",
    },
    {
        "industry_code": "food",
        "code": "GB 2760-2011",
        "name": "食品安全国家标准 食品添加剂使用标准",
        "version": "2011",
        "effective_date": "2011-06-20",
        "filename": "gb_2760_2011_nhc.pdf",
        "source": "国家卫生健康委员会公开文件",
    },
    {
        "industry_code": "food",
        "code": "GB 2760-2024",
        "name": "食品安全国家标准 食品添加剂使用标准",
        "version": "2024",
        "effective_date": "2025-02-08",
        "filename": "gb_2760_2024_cfaa.pdf",
        "source": "中国食品添加剂和配料协会公开文件备份",
    },
    {
        "industry_code": "food",
        "code": "GB 7718-2025",
        "name": "食品安全国家标准 预包装食品标签通则",
        "version": "2025",
        "effective_date": "2027-03-16",
        "filename": "gb_7718_2025_chemanaly.pdf",
        "source": "第三方公开标准文件备份",
    },
    {
        "industry_code": "food",
        "code": "GB 28050-2025",
        "name": "食品安全国家标准 预包装食品营养标签通则",
        "version": "2025",
        "effective_date": "2027-03-16",
        "filename": "gb_28050_2025_chemanaly.pdf",
        "source": "第三方公开标准文件备份",
    },
    {
        "industry_code": "food",
        "code": "食品召回管理办法",
        "name": "食品召回管理办法",
        "version": "2020修订",
        "effective_date": "2020-10-23",
        "filename": "food_recall_measures.pdf",
        "source": "市场监督管理总局规章库公开文件",
    },
    {
        "industry_code": "pet_food",
        "code": "农业农村部公告第20号",
        "name": "宠物饲料管理办法及配套规范",
        "version": "2018",
        "effective_date": "2018-06-01",
        "filename": "pet_feed_moa_announcement_20.pdf",
        "source": "农业农村部公告第20号公开文件",
    },
    {
        "industry_code": "electronics",
        "code": "CNCA-C09-01:2023",
        "name": "强制性产品认证实施规则 电子产品及安全附件",
        "version": "2023",
        "effective_date": "2023-08-01",
        "filename": "ccc_cnca_c09_01_2023.html",
        "source": "国家认监委公开文件",
    },
    {
        "industry_code": "electronics",
        "code": "GB 4943.1-2022",
        "name": "音视频、信息技术和通信技术设备 第1部分：安全要求",
        "version": "2022",
        "effective_date": "2023-08-01",
        "filename": "gb_4943_1_2022_yiqifuwu.pdf",
        "source": "第三方公开标准文件备份",
    },
    {
        "industry_code": "electronics",
        "code": "GB 31241-2022",
        "name": "便携式电子产品用锂离子电池和电池组 安全技术规范",
        "version": "2022",
        "effective_date": "2024-08-01",
        "filename": "gb_31241_2022_ocr.txt",
        "source": "第三方公开标准 PDF 离线 OCR 文本",
    },
    {
        "industry_code": "electronics",
        "code": "GB 26572-2025",
        "name": "电器电子产品有害物质限制使用要求",
        "version": "2025",
        "effective_date": "2027-08-01",
        "filename": "gb_26572_2025_hubei_jxt.pdf",
        "source": "湖北省经济和信息化厅公开文件",
    },
]


def seed_official_fulltext_pack(db: Session, industries: dict[str, Any]) -> int:
    created_chunks = 0
    for item in OFFICIAL_FULLTEXT_PACK:
        industry = industries.get(item["industry_code"])
        if not industry:
            continue
        path = OFFICIAL_FULLTEXT_DIR / item["filename"]
        if not path.exists():
            continue
        standard = _upsert_standard(db, industry.id, item, str(path))
        if _has_fulltext_chunks(db, standard.id, str(path)):
            continue
        parsed = get_document_parser().parse(str(path))
        text = str(parsed.get("text") or "")
        chunks = chunk_standard_text(text)
        if not chunks:
            continue
        for existing in db.scalars(select(StandardClause).where(StandardClause.standard_id == standard.id)):
            db.delete(existing)
        for index, chunk in enumerate(chunks, 1):
            db.add(
                StandardClause(
                    standard_id=standard.id,
                    industry_id=industry.id,
                    clause_no=chunk.clause_no[:80],
                    title=chunk.title[:240],
                    content=chunk.content,
                    page_no=chunk.page_no[:40],
                    source_file=str(path),
                    chunk_index=index,
                    status="active",
                )
            )
        standard.clauses = dumps(
            [
                {"no": chunk.clause_no, "title": chunk.title, "content": chunk.content[:500], "source": item["source"]}
                for chunk in chunks[:20]
            ]
        )
        created_chunks += len(chunks)
    return created_chunks


def _upsert_standard(db: Session, industry_id: str, item: dict[str, Any], source_file: str) -> Standard:
    standard = db.scalar(
        select(Standard).where(Standard.industry_id == industry_id, Standard.code == item["code"])
    )
    if standard:
        standard.name = item["name"]
        standard.version = item["version"]
        standard.effective_date = item["effective_date"]
        standard.source_file = source_file
        standard.status = "active"
        return standard
    standard = Standard(
        industry_id=industry_id,
        code=item["code"],
        name=item["name"],
        version=item["version"],
        effective_date=item["effective_date"],
        source_file=source_file,
        clauses=dumps([]),
        status="active",
    )
    db.add(standard)
    db.flush()
    return standard


def _has_fulltext_chunks(db: Session, standard_id: str, source_file: str) -> bool:
    clauses = list(
        db.scalars(
            select(StandardClause).where(
                StandardClause.standard_id == standard_id,
                StandardClause.source_file == source_file,
                StandardClause.status == "active",
            )
        )
    )
    return bool(clauses)
