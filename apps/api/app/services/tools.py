from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditRule, DetectionItem, ModelProvider, Standard, StandardClause
from app.services.document_parser import get_document_parser


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _command_available(name: str) -> bool:
    if shutil.which(name):
        return True
    if platform.system() == "Windows":
        home = Path(os.environ.get("USERPROFILE", str(Path.home())))
        extra_dirs = [home / ".cargo" / "bin"]
        suffixes = [".exe", ".cmd", ".bat", ""]
        for directory in extra_dirs:
            for suffix in suffixes:
                if (directory / f"{name}{suffix}").exists():
                    return True
    return False


def _status(ready: bool, partial: bool = False) -> str:
    if ready:
        return "ready"
    if partial:
        return "partial"
    return "missing"


def _detail(label: str, ok: bool, note: str = "") -> dict[str, Any]:
    return {"label": label, "ok": ok, "note": note}


def _count(db: Session, model: type[Any], *where: Any) -> int:
    statement = select(func.count()).select_from(model)
    for condition in where:
        statement = statement.where(condition)
    return int(db.scalar(statement) or 0)


def get_tool_statuses(db: Session) -> dict[str, Any]:
    settings = get_settings()
    system = platform.system()
    is_macos = system == "Darwin"
    is_windows = system == "Windows"
    macos_vision_ready = is_macos and Path("/usr/bin/swift").exists()
    paddle_ready = _module_available("paddleocr")
    rapid_ready = _module_available("rapidocr_onnxruntime") or _module_available("rapidocr")
    tesseract_ready = _command_available("tesseract")
    ocr_ready_count = sum([macos_vision_ready, paddle_ready, rapid_ready, tesseract_ready])

    mineru_ready = _command_available("magic-pdf") or _command_available("mineru") or bool(settings.mineru_command.strip())
    docling_ready = _module_available("docling")
    pypdf_ready = _module_available("pypdf")
    docx_ready = _module_available("docx")

    active_clauses = _count(db, StandardClause, StandardClause.status == "active")
    active_standards = _count(db, Standard, Standard.status == "active")
    active_rules = _count(db, AuditRule, AuditRule.status == "active")
    active_quotes = _count(db, DetectionItem, DetectionItem.status == "active")
    active_models = _count(db, ModelProvider, ModelProvider.status == "active")
    keyed_models = _count(
        db,
        ModelProvider,
        ModelProvider.status == "active",
        ModelProvider.api_key_secret != "",
    )

    report_pdf_ready = _module_available("playwright")
    report_excel_ready = _module_available("openpyxl")
    report_word_ready = True
    docxtpl_ready = _module_available("docxtpl")
    weasyprint_ready = _module_available("weasyprint")
    python_ready = _command_available("python") or _command_available("py") or _command_available("python3")
    pnpm_ready = _command_available("pnpm")
    cargo_ready = _command_available("cargo")
    windows_ocr_ready = rapid_ready or paddle_ready or tesseract_ready
    windows_data_ready = is_windows and "HuianInspectionAI" in str(settings.upload_dir)

    tools = [
        {
            "id": "windows_runtime",
            "name": "Windows 运行环境",
            "category": "应用发布",
            "status": _status(
                is_windows and python_ready and pnpm_ready and windows_ocr_ready and windows_data_ready,
                partial=(not is_windows) or (python_ready or pnpm_ready or windows_ocr_ready),
            ),
            "enabled": is_windows,
            "summary": "Windows 优先运行检查：本地数据目录、OCR 保底、前后端启动和桌面打包依赖。",
            "details": [
                _detail("当前系统", is_windows, "Windows 优先目标" if is_windows else f"当前为 {system or '未知系统'}"),
                _detail("本地数据目录", windows_data_ready or not is_windows, str(settings.upload_dir)),
                _detail("Python", python_ready, "后端服务运行环境"),
                _detail("pnpm", pnpm_ready, "前端和桌面启动工具"),
                _detail("本地 OCR", windows_ocr_ready, "Windows 建议内置 RapidOCR"),
                _detail("Rust/Cargo", cargo_ready, "Tauri 安装包构建需要"),
            ],
            "install_hint": "Windows 正式版建议运行 scripts/windows-setup.ps1，并优先安装 RapidOCR。",
            "github": ["RapidAI/RapidOCR", "tauri-apps/tauri"],
        },
        {
            "id": "ocr_cascade",
            "name": "OCR 多引擎识别",
            "category": "视觉识别",
            "status": _status(ocr_ready_count > 0, partial=ocr_ready_count > 0),
            "enabled": True,
            "summary": "上传图片后先走本地 OCR 级联，DeepSeek 等无视觉模型也能拿到文字。",
            "details": [
                _detail("macOS Vision", macos_vision_ready, "Mac 本机保底 OCR" if is_macos else "仅 macOS 可用"),
                _detail("PaddleOCR", paddle_ready, "适合中文复杂标签，未安装时不影响其它 OCR"),
                _detail("RapidOCR", rapid_ready, "轻量 ONNX OCR，适合桌面打包"),
                _detail("Tesseract", tesseract_ready, "传统 OCR 保底，需要系统二进制"),
            ],
            "install_hint": "可选增强：安装 rapidocr-onnxruntime 或 PaddleOCR；Windows/Mac 打包优先 RapidOCR。",
            "github": ["PaddlePaddle/PaddleOCR", "RapidAI/RapidOCR", "tesseract-ocr/tesseract"],
        },
        {
            "id": "document_parser",
            "name": "PDF/Word 文档解析",
            "category": "资料导入",
            "status": _status(pypdf_ready or docx_ready or mineru_ready or docling_ready, partial=pypdf_ready or docx_ready),
            "enabled": True,
            "summary": "法规全文、报价文档导入时，把 PDF/Word/TXT 转为可切片文本。",
            "details": [
                _detail("MinerU", mineru_ready, "复杂 PDF 版面解析增强"),
                _detail("Docling", docling_ready, "PDF/Office 结构化解析增强"),
                _detail("pypdf", pypdf_ready, "当前 PDF 文本抽取"),
                _detail("python-docx", docx_ready, "当前 Word 文档抽取"),
            ],
            "install_hint": "可选增强：MinerU 适合标准 PDF；Docling 适合结构化文档解析。",
            "github": ["opendatalab/MinerU", "docling-project/docling"],
        },
        {
            "id": "knowledge_retrieval",
            "name": "本地法规检索",
            "category": "知识库",
            "status": _status(active_clauses > 0, partial=active_standards > 0),
            "enabled": True,
            "summary": "按品类路由后，只检索对应法规全文切片，减少模型上下文浪费。",
            "metrics": {"standards": active_standards, "clauses": active_clauses},
            "details": [
                _detail("标准/法规", active_standards > 0, f"{active_standards} 条 active"),
                _detail("全文切片", active_clauses > 0, f"{active_clauses} 个 active"),
            ],
            "install_hint": "已内置本地 SQLite 检索；后续可替换为 LlamaIndex/Haystack 向量检索。",
            "github": ["run-llama/llama_index", "deepset-ai/haystack"],
        },
        {
            "id": "rule_engine",
            "name": "确定性规则校验",
            "category": "审核工具",
            "status": _status(active_rules > 0),
            "enabled": True,
            "summary": "对配料表、净含量、生产许可、营养成分、警示语等硬性字段做自动校验。",
            "metrics": {"rules": active_rules},
            "details": [_detail("审核规则", active_rules > 0, f"{active_rules} 条 active")],
            "install_hint": "当前为内置规则引擎；适合继续补充品类硬性规则。",
            "github": [],
        },
        {
            "id": "report_generator",
            "name": "报告生成",
            "category": "输出",
            "status": _status(report_pdf_ready and report_excel_ready and report_word_ready, partial=report_pdf_ready or report_excel_ready),
            "enabled": True,
            "summary": "审核结果可导出 PDF，报价可导出 PDF/Excel，前端可生成 Word 报告。",
            "details": [
                _detail("PDF", report_pdf_ready, "Playwright 渲染报告"),
                _detail("Excel", report_excel_ready, "openpyxl 生成报价明细"),
                _detail("Word", report_word_ready, "前端生成可打开的 Word 文档"),
                _detail("docxtpl", docxtpl_ready, "正式 Word 模板增强"),
                _detail("WeasyPrint", weasyprint_ready, "PDF 渲染备选"),
            ],
            "install_hint": "可选增强：docxtpl 生成正式 Word 模板，WeasyPrint 可作为 PDF 备选。",
            "github": ["elapouya/python-docx-template", "Kozea/WeasyPrint"],
        },
        {
            "id": "quote_library",
            "name": "项目报价库",
            "category": "报价",
            "status": _status(active_quotes > 0),
            "enabled": True,
            "summary": "支持单项维护和文档导入，审核风险项可匹配检测/审核项目并生成报价单。",
            "metrics": {"items": active_quotes},
            "details": [_detail("报价项目", active_quotes > 0, f"{active_quotes} 条 active")],
            "install_hint": "已接入当前工作流。",
            "github": [],
        },
        {
            "id": "model_gateway",
            "name": "模型网关",
            "category": "模型",
            "status": _status(active_models > 0, partial=keyed_models > 0),
            "enabled": True,
            "summary": "统一接入 GPT、Claude、DeepSeek、豆包等 OpenAI-compatible 或自定义供应商。",
            "metrics": {"providers": active_models, "with_keys": keyed_models},
            "details": [
                _detail("模型配置", active_models > 0, f"{active_models} 个 active"),
                _detail("API Key", keyed_models > 0, f"{keyed_models} 个已保存密钥"),
            ],
            "install_hint": "如需更强兼容层，可接入 LiteLLM。",
            "github": ["BerriAI/litellm"],
        },
        {
            "id": "agent_orchestrator",
            "name": "智能体编排",
            "category": "智能体",
            "status": _status(_module_available("langgraph"), partial=_module_available("llama_index") or _module_available("haystack")),
            "enabled": False,
            "summary": "用于把 OCR、法规检索、规则校验、模型复核、报告生成组织成可观测流程。",
            "details": [
                _detail("LangGraph", _module_available("langgraph"), "推荐作为正式 agent 状态机"),
                _detail("LlamaIndex", _module_available("llama_index"), "可用于法规 RAG"),
                _detail("Haystack", _module_available("haystack"), "可用于检索管线"),
            ],
            "install_hint": "当前用后端固定编排，稳定优先；正式 agent 化建议先接 LangGraph。",
            "github": ["langchain-ai/langgraph", "run-llama/llama_index", "deepset-ai/haystack"],
        },
        {
            "id": "desktop_packager",
            "name": "Mac/Windows 桌面打包",
            "category": "应用发布",
            "status": _status(cargo_ready and pnpm_ready, partial=pnpm_ready),
            "enabled": False,
            "summary": "将 React 工作台和 FastAPI sidecar 打包成 Mac/Windows 可安装应用。",
            "details": [
                _detail("pnpm", pnpm_ready, "前端构建工具"),
                _detail("Rust/Cargo", cargo_ready, "Tauri 打包需要"),
            ],
            "install_hint": "推荐 Tauri + FastAPI sidecar，OCR 模型和法规库随安装包内置。",
            "github": ["tauri-apps/tauri"],
        },
    ]

    ready = sum(1 for item in tools if item["status"] == "ready")
    partial = sum(1 for item in tools if item["status"] == "partial")
    missing = sum(1 for item in tools if item["status"] == "missing")
    return {
        "tools": tools,
        "summary": {"ready": ready, "partial": partial, "missing": missing, "total": len(tools)},
    }


def test_tool(db: Session, tool_id: str) -> dict[str, Any]:
    statuses = get_tool_statuses(db)
    tool = next((item for item in statuses["tools"] if item["id"] == tool_id), None)
    if not tool:
        return {"tool_id": tool_id, "status": "missing", "message": "未找到该工具。"}

    if tool_id == "document_parser":
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as file:
            file.write("标准名称：测试文件\n条款：标签应清晰。")
            path = Path(file.name)
        try:
            parsed = get_document_parser().parse(str(path), path.read_bytes())
            ok = bool(str(parsed.get("text") or "").strip())
            return {
                "tool_id": tool_id,
                "status": "ready" if ok else "missing",
                "message": "文档解析测试通过。" if ok else "文档解析未能读取测试文本。",
                "details": {"provider": parsed.get("provider"), "text_length": len(str(parsed.get("text") or ""))},
            }
        finally:
            path.unlink(missing_ok=True)

    if tool_id == "knowledge_retrieval":
        clause = db.scalar(select(StandardClause).where(StandardClause.status == "active").limit(1))
        if clause:
            return {
                "tool_id": tool_id,
                "status": "ready",
                "message": f"法规检索可用，已读到条款：{clause.clause_no or clause.title or clause.id[:8]}。",
            }
        return {"tool_id": tool_id, "status": "missing", "message": "法规全文切片为空，请先导入或重新构建知识库。"}

    if tool_id == "rule_engine":
        count = _count(db, AuditRule, AuditRule.status == "active")
        return {
            "tool_id": tool_id,
            "status": "ready" if count else "missing",
            "message": f"规则库可用，当前 {count} 条 active 规则。" if count else "规则库为空。",
        }

    if tool_id == "quote_library":
        count = _count(db, DetectionItem, DetectionItem.status == "active")
        return {
            "tool_id": tool_id,
            "status": "ready" if count else "missing",
            "message": f"报价库可用，当前 {count} 条 active 项目。" if count else "报价库为空。",
        }

    if tool_id == "model_gateway":
        count = _count(db, ModelProvider, ModelProvider.status == "active")
        keyed = _count(db, ModelProvider, ModelProvider.status == "active", ModelProvider.api_key_secret != "")
        return {
            "tool_id": tool_id,
            "status": "ready" if count else "missing",
            "message": f"模型网关可用，{count} 个供应商，{keyed} 个已保存密钥。" if count else "尚未配置模型供应商。",
        }

    return {
        "tool_id": tool_id,
        "status": tool["status"],
        "message": f"{tool['name']} 状态：{tool['status']}。{tool.get('install_hint', '')}",
        "details": tool.get("details", []),
    }
