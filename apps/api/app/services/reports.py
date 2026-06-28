from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.config import get_settings
from app.json_utils import loads
from app.models import AuditTask, Quote
from app.services.quotes import recommend_items_for_audit


def _escape(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _money(value: Any) -> str:
    try:
        return f"¥{float(value):,.2f}"
    except (TypeError, ValueError):
        return "¥0.00"


def _risk_label(level: str) -> str:
    return {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(level, level or "未分级")


def _status_label(status: str) -> str:
    return {
        "pending": "待处理",
        "completed": "已完成",
        "needs_review": "需人工复核",
        "failed": "失败",
        "draft": "草稿",
    }.get(status, status or "-")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _plain(value: Any, limit: int | None = None) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        return text[: limit - 1] + "..."
    return text


def _register_pdf_font() -> str:
    font_name = "STSong-Light"
    try:
        pdfmetrics.getFont(font_name)
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def _pdf_styles() -> dict[str, ParagraphStyle]:
    font = _register_pdf_font()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "HuianTitle",
            parent=base["Title"],
            fontName=font,
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#111814"),
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "HuianHeading",
            parent=base["Heading2"],
            fontName=font,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#111814"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "HuianBody",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#26322b"),
        ),
        "small": ParagraphStyle(
            "HuianSmall",
            parent=base["BodyText"],
            fontName=font,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#5c675f"),
        ),
    }


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_escape(_plain(value)), style)


def _pdf_table(rows: list[list[Any]], widths: list[float] | None = None) -> Table:
    styles = _pdf_styles()
    converted = [[cell if hasattr(cell, "wrap") else _p(cell, styles["body"]) for cell in row] for row in rows]
    table = Table(converted, colWidths=widths, repeatRows=1 if len(rows) > 1 else 0)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#39473f")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dfe4dc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_audit_story(task: AuditTask) -> list[Any]:
    styles = _pdf_styles()
    report = loads(task.final_report, {})
    fields = loads(task.extracted_fields, {})
    findings = report.get("findings", []) if isinstance(report.get("findings"), list) else []
    quote_items = _quote_items_for_task(task)
    story: list[Any] = [
        _p("汇安检测合规审核报告", styles["title"]),
        _p(report.get("summary") or "系统已生成结构化审核结果。", styles["body"]),
        Spacer(1, 6),
    ]
    meta_rows = [
        ["客户", task.customer_name or "-", "文档类型", task.document_type or "-"],
        ["审核状态", _status_label(task.status), "生成时间", _today()],
        ["模型", task.model_used or "-", "行业", report.get("industry") or "-"],
    ]
    story.append(_pdf_table(meta_rows, [28 * mm, 56 * mm, 28 * mm, 56 * mm]))
    story.extend([Spacer(1, 8), _p("识别字段", styles["heading"])])
    field_labels = [
        ("product_name", "产品名称"),
        ("ingredients", "配料"),
        ("nutrition", "营养信息"),
        ("net_content", "净含量"),
        ("license_no", "许可证编号"),
        ("manufacturer", "生产者"),
        ("address", "地址"),
        ("shelf_life", "保质期"),
        ("production_date", "生产日期"),
        ("execution_standard", "执行标准"),
    ]
    field_rows = [["字段", "内容"]]
    for key, label in field_labels:
        value = fields.get(key)
        if value not in (None, "", [], {}):
            field_rows.append([label, _plain(value, 320)])
    story.append(_pdf_table(field_rows if len(field_rows) > 1 else [["字段", "内容"], ["抽取字段", "暂无可展示字段"]], [34 * mm, 134 * mm]))

    story.extend([Spacer(1, 8), _p("风险详情", styles["heading"])])
    if not findings:
        story.append(_p("本次审核未发现明确风险项，仍建议人工抽查关键字段和依据版本。", styles["body"]))
    for index, finding in enumerate(findings, 1):
        source = " ".join(
            part
            for part in [
                _plain(finding.get("standard_code")),
                _plain(finding.get("standard_clause")),
                _plain(finding.get("source_excerpt"), 900),
            ]
            if part
        )
        story.append(_p(f"{index}. {_plain(finding.get('title') or '风险提示')}（{_risk_label(str(finding.get('risk_level') or 'medium'))}）", styles["heading"]))
        story.append(
            _pdf_table(
                [
                    ["项目", "内容"],
                    ["标签原文", _plain(finding.get("evidence_text"), 420) or "-"],
                    ["问题说明", _plain(finding.get("reason"), 420) or "-"],
                    ["法规依据", source or "依据标准规则库匹配结果生成，需结合源文件条款复核。"],
                    ["修改建议", _plain(finding.get("suggestion"), 420) or "-"],
                    ["置信度", _plain(finding.get("confidence")) or "-"],
                ],
                [28 * mm, 140 * mm],
            )
        )

    story.extend([Spacer(1, 8), _p("推荐检测与报价项目", styles["heading"])])
    if quote_items:
        quote_rows = [["编号", "项目", "标准", "样品要求", "周期", "价格"]]
        for item in quote_items:
            quote_rows.append(
                [
                    item.get("code") or "-",
                    _plain(item.get("name"), 120) or "-",
                    _plain(item.get("method_standard") or item.get("judgment_standard"), 160) or "-",
                    _plain(item.get("sample_amount"), 100) or "-",
                    f"{item.get('cycle_days') or '-'} 天",
                    _money(item.get("price")),
                ]
            )
        story.append(_pdf_table(quote_rows, [18 * mm, 38 * mm, 42 * mm, 30 * mm, 18 * mm, 22 * mm]))
    else:
        story.append(_p("暂无自动匹配的报价项目。", styles["body"]))
    story.extend(
        [
            Spacer(1, 10),
            _p("声明：AI 结果仅供参考，不构成法律意见、官方检测结论或监管认定。标准依据和报价项目应结合源文件版本、客户样品状态和实验室受理规则进行人工确认。", styles["small"]),
            _p(f"Report ID: {task.id}", styles["small"]),
        ]
    )
    return story


def _build_quote_story(quote: Quote) -> list[Any]:
    styles = _pdf_styles()
    items = loads(quote.items_json, [])
    story: list[Any] = [
        _p("检测服务报价单", styles["title"]),
        _p("根据审核报告中识别的风险项、推荐检测项目和当前项目报价库自动生成。最终受理范围、周期和费用以实验室确认及双方约定为准。", styles["body"]),
        Spacer(1, 6),
        _pdf_table(
            [
                ["报价单号", quote.quote_no, "客户", quote.customer_name or "-"],
                ["有效期至", quote.valid_until.date().isoformat(), "生成时间", _today()],
                ["小计", _money(quote.subtotal), "合计", _money(quote.total)],
            ],
            [28 * mm, 56 * mm, 28 * mm, 56 * mm],
        ),
        Spacer(1, 8),
        _p("报价明细", styles["heading"]),
    ]
    if items:
        rows = [["编号", "项目", "标准", "样品要求", "周期", "价格"]]
        for item in items:
            rows.append(
                [
                    item.get("code") or "-",
                    _plain(item.get("name"), 120) or "-",
                    _plain(item.get("method_standard"), 160) or "-",
                    _plain(item.get("sample_amount"), 100) or "-",
                    f"{item.get('cycle_days') or '-'} 天",
                    _money(item.get("price")),
                ]
            )
        rows.append(["", "", "", "", "合计", _money(quote.total)])
        story.append(_pdf_table(rows, [18 * mm, 38 * mm, 42 * mm, 30 * mm, 18 * mm, 22 * mm]))
    else:
        story.append(_p("暂无报价项目。", styles["body"]))
    story.extend(
        [
            Spacer(1, 10),
            _p("说明：报价由项目报价库自动匹配生成，样品量、检测周期和检测标准需结合实际样品和实验室能力复核。加急、复测、分包、发票税率等费用以最终确认单为准。", styles["small"]),
            _p(f"Quote ID: {quote.id}", styles["small"]),
        ]
    )
    return story


def _render_story_pdf(story: list[Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=15 * mm,
        title="汇安检测报告",
    )
    document.build(story)
    return path


def _base_css() -> str:
    return """
    @page {
      size: A4;
      margin: 14mm 13mm 16mm;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: #17201c;
      background: #f5f3ef;
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
      font-size: 12px;
      line-height: 1.6;
    }
    .page {
      background: #fffdf9;
      min-height: 100vh;
      padding: 26px 28px 22px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 22px;
      align-items: start;
      padding-bottom: 18px;
      border-bottom: 1px solid #d8ddd6;
    }
    .eyebrow {
      color: #5c6b62;
      font-size: 11px;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    h1 {
      margin: 5px 0 8px;
      font-size: 26px;
      line-height: 1.18;
      font-weight: 760;
      color: #111814;
    }
    h2 {
      margin: 24px 0 10px;
      font-size: 15px;
      color: #111814;
    }
    h3 {
      margin: 0 0 8px;
      font-size: 13px;
      color: #111814;
    }
    .summary {
      max-width: 610px;
      color: #425047;
      font-size: 12.5px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 11px;
      font-weight: 650;
      white-space: nowrap;
      border: 1px solid transparent;
    }
    .badge.high { color: #8a1f17; background: #ffe8e4; border-color: #f5c3bb; }
    .badge.medium { color: #7a4a05; background: #fff2cf; border-color: #edd189; }
    .badge.low { color: #17624c; background: #dff6ec; border-color: #a9deca; }
    .badge.neutral { color: #314139; background: #eef1ed; border-color: #d7ddd7; }
    .meta-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin: 16px 0 4px;
    }
    .meta {
      min-height: 58px;
      padding: 10px 11px;
      border: 1px solid #dde1da;
      border-radius: 10px;
      background: #fbfaf6;
    }
    .meta span {
      display: block;
      color: #758077;
      font-size: 10.5px;
      margin-bottom: 3px;
    }
    .meta strong {
      display: block;
      color: #17201c;
      font-size: 12px;
      font-weight: 680;
      word-break: break-word;
    }
    .section {
      break-inside: avoid;
    }
    .field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 10px;
      margin-top: 8px;
    }
    .field {
      padding: 9px 10px;
      border: 1px solid #e1e5de;
      background: #fff;
      border-radius: 8px;
    }
    .field span {
      display: block;
      color: #778178;
      font-size: 10.5px;
      margin-bottom: 2px;
    }
    .field strong {
      color: #1e2923;
      font-weight: 580;
    }
    .finding {
      break-inside: avoid;
      margin: 10px 0;
      border: 1px solid #dfe4dc;
      border-radius: 12px;
      background: #fff;
      overflow: hidden;
    }
    .finding-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
      padding: 12px 14px;
      background: #f7f8f4;
      border-bottom: 1px solid #e1e5de;
    }
    .finding-title {
      font-size: 14px;
      font-weight: 720;
      color: #121a15;
    }
    .finding-body {
      padding: 12px 14px 14px;
      display: grid;
      gap: 9px;
    }
    .kv {
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 10px;
    }
    .kv b {
      color: #6d776f;
      font-weight: 620;
    }
    .kv div {
      color: #26322b;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #dfe4dc;
      border-radius: 10px;
      overflow: hidden;
    }
    thead { display: table-header-group; }
    th {
      background: #eef2eb;
      color: #39473f;
      text-align: left;
      font-size: 11px;
      padding: 8px 8px;
      border-bottom: 1px solid #d9dfd6;
    }
    td {
      padding: 8px;
      vertical-align: top;
      border-bottom: 1px solid #edf0eb;
      color: #26322b;
      word-break: break-word;
    }
    tr:last-child td { border-bottom: none; }
    .total-row td {
      background: #f7f8f4;
      font-weight: 720;
    }
    .note {
      margin-top: 20px;
      padding: 10px 12px;
      background: #f7f8f4;
      border: 1px solid #dfe4dc;
      border-radius: 10px;
      color: #5c675f;
      font-size: 11px;
    }
    .footer {
      margin-top: 20px;
      color: #8a928b;
      font-size: 10px;
      display: flex;
      justify-content: space-between;
      border-top: 1px solid #e2e6df;
      padding-top: 10px;
    }
    """


def _render_pdf(html_content: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1754})
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=str(path),
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    return path


def _quote_for_task(task_id: str) -> Quote | None:
    with SessionLocal() as db:
        quote = db.scalar(select(Quote).where(Quote.audit_task_id == task_id).order_by(Quote.created_at.desc()))
        return quote


def _quote_items_for_task(task: AuditTask) -> list[dict[str, Any]]:
    quote = _quote_for_task(task.id)
    if quote:
        return loads(quote.items_json, [])
    with SessionLocal() as db:
        attached_task = db.merge(task, load=False)
        return [
            {
                "code": item.code,
                "name": item.name,
                "method_standard": item.method_standard,
                "judgment_standard": item.judgment_standard,
                "sample_amount": item.sample_amount,
                "price": item.price,
                "cycle_days": item.cycle_days,
                "lab_name": "待分配实验室",
            }
            for item in recommend_items_for_audit(db, attached_task)
        ]


def _fields_html(fields: dict[str, Any]) -> str:
    labels = [
        ("product_name", "产品名称"),
        ("product_type", "产品类别"),
        ("net_content", "净含量"),
        ("shelf_life", "保质期"),
        ("production_date", "生产日期"),
        ("expiry_date", "到期日期"),
        ("license_no", "许可证编号"),
        ("manufacturer", "生产者"),
        ("address", "地址"),
        ("execution_standard", "执行标准"),
        ("storage_condition", "贮存条件"),
        ("ingredients", "配料"),
        ("nutrition", "营养信息"),
    ]
    items = []
    for key, label in labels:
        value = fields.get(key)
        if value in (None, "", [], {}):
            continue
        items.append(f'<div class="field"><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>')
    return "".join(items) or '<div class="field"><span>抽取字段</span><strong>暂无可展示字段</strong></div>'


def _findings_html(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return '<div class="note">本次审核未发现明确风险项，仍建议人工抽查关键字段和依据版本。</div>'
    cards = []
    for index, finding in enumerate(findings, 1):
        level = str(finding.get("risk_level") or "medium")
        standard = " / ".join(
            value
            for value in [
                str(finding.get("standard_code") or ""),
                str(finding.get("standard_clause") or ""),
                str(finding.get("source_excerpt") or ""),
            ]
            if value
        )
        items = "、".join(finding.get("recommended_item_codes") or [])
        cards.append(
            f"""
            <article class="finding">
              <div class="finding-head">
                <div>
                  <div class="eyebrow">Finding {index:02d}</div>
                  <div class="finding-title">{_escape(finding.get("title") or "风险提示")}</div>
                </div>
                <span class="badge {level}">{_escape(_risk_label(level))}</span>
              </div>
              <div class="finding-body">
                <div class="kv"><b>触发字段</b><div>{_escape(finding.get("field_key") or "模型/OCR 综合识别")}</div></div>
                <div class="kv"><b>识别证据</b><div>{_escape(finding.get("evidence_text") or "-")}</div></div>
                <div class="kv"><b>风险原因</b><div>{_escape(finding.get("reason") or "-")}</div></div>
                <div class="kv"><b>引用依据</b><div>{_escape(standard or "依据标准规则库匹配结果生成，需结合源文件条款复核。")}</div></div>
                <div class="kv"><b>整改建议</b><div>{_escape(finding.get("suggestion") or "-")}</div></div>
                <div class="kv"><b>复核信息</b><div>置信度 {_escape(finding.get("confidence") or "-")}；{ "建议人工复核" if finding.get("needs_human_review") else "可自动通过" }；推荐项目：{_escape(items or "暂无")}</div></div>
              </div>
            </article>
            """
        )
    return "".join(cards)


def _quote_table_html(items: list[dict[str, Any]], include_total: bool = False, total: float | None = None) -> str:
    if not items:
        return '<div class="note">暂无自动匹配的报价项目。</div>'
    rows = []
    subtotal = 0.0
    for item in items:
        price = float(item.get("price") or 0)
        subtotal += price
        rows.append(
            f"""
            <tr>
              <td>{_escape(item.get("code") or "-")}</td>
              <td>{_escape(item.get("name") or "-")}</td>
              <td>{_escape(item.get("method_standard") or item.get("judgment_standard") or "-")}</td>
              <td>{_escape(item.get("sample_amount") or "-")}</td>
              <td>{_escape(item.get("cycle_days") or "-")} 天</td>
              <td>{_money(price)}</td>
            </tr>
            """
        )
    if include_total:
        rows.append(
            f"""
            <tr class="total-row">
              <td colspan="5">合计</td>
              <td>{_money(total if total is not None else subtotal)}</td>
            </tr>
            """
        )
    return f"""
      <table>
        <thead>
          <tr>
            <th style="width: 12%;">编号</th>
            <th style="width: 24%;">项目</th>
            <th style="width: 22%;">检测/判定标准</th>
            <th style="width: 20%;">样品要求</th>
            <th style="width: 10%;">周期</th>
            <th style="width: 12%;">价格</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    """


def generate_audit_pdf(task: AuditTask) -> Path:
    settings = get_settings()
    path = settings.report_dir / f"audit-{task.id}.pdf"
    return _render_story_pdf(_build_audit_story(task), path)


def generate_quote_pdf(quote: Quote) -> Path:
    settings = get_settings()
    path = settings.report_dir / f"quote-{quote.id}.pdf"
    return _render_story_pdf(_build_quote_story(quote), path)


def generate_quote_xlsx(quote: Quote) -> Path:
    settings = get_settings()
    path = settings.report_dir / f"quote-{quote.id}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "报价单"
    ws.append(["报价单号", quote.quote_no])
    ws.append(["客户", quote.customer_name])
    ws.append(["有效期", quote.valid_until.date().isoformat()])
    ws.append([])
    ws.append(["项目编号", "检测项目", "标准", "推荐实验室", "资质", "样品要求", "单价", "周期"])
    for item in loads(quote.items_json, []):
        ws.append(
            [
                item.get("code"),
                item.get("name"),
                item.get("method_standard"),
                item.get("lab_name"),
                item.get("lab_qualification"),
                item.get("sample_amount"),
                item.get("price"),
                item.get("cycle_days"),
            ]
        )
    ws.append([])
    ws.append(["小计", quote.subtotal])
    ws.append(["折扣", quote.discount_rate])
    ws.append(["税率", quote.tax_rate])
    ws.append(["合计", quote.total])
    wb.save(path)
    return path
