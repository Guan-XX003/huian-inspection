import base64
import json
import mimetypes
import os
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.models import ModelProvider


FIELD_KEYS = [
    "product_name",
    "product_type",
    "net_content",
    "shelf_life",
    "production_date",
    "expiry_date",
    "license_no",
    "manufacturer",
    "address",
    "phone",
    "execution_standard",
    "ingredients",
    "additives",
    "allergens",
    "nutrition",
    "nutrition_tables",
    "claims",
    "claims_or_marketing_words",
    "storage_condition",
    "target_pet",
    "feeding_instruction",
    "model_no",
    "rating",
    "certification",
    "manual_warning",
    "unreadable_parts",
]


class ModelGateway:
    timeout_seconds = 240
    max_vision_image_edge = 1400
    vision_image_quality = 78
    max_rules_in_prompt = 18

    def parse_library_document(
        self,
        provider: Optional[ModelProvider],
        target_library: str,
        industry_name: str,
        filename: str,
        text: str,
    ) -> dict[str, Any]:
        api_key = self._resolve_api_key(provider)
        base_url = self._resolve_base_url(provider)
        if provider and base_url and api_key:
            try:
                return self._parse_library_remote(provider, api_key, base_url, target_library, industry_name, filename, text)
            except Exception as exc:
                parsed = self._parse_library_local(target_library, industry_name, filename, text)
                parsed["model_note"] = f"真实模型解析失败，已使用本地保守解析：{type(exc).__name__}: {exc}"
                return parsed
        parsed = self._parse_library_local(target_library, industry_name, filename, text)
        parsed["model_note"] = "未配置真实模型密钥，当前使用本地保守解析。"
        return parsed

    def analyze(
        self,
        provider: Optional[ModelProvider],
        industry_name: str,
        ocr_result: dict,
        fields: dict,
        rule_results: list[dict],
        file_path: str,
    ) -> dict:
        api_key = self._resolve_api_key(provider)
        base_url = self._resolve_base_url(provider)
        if provider and base_url and api_key:
            try:
                return self._analyze_remote(provider, api_key, industry_name, ocr_result, fields, rule_results, file_path, base_url)
            except Exception as exc:
                return self._mock_analyze(
                    provider,
                    industry_name,
                    ocr_result,
                    fields,
                    rule_results,
                    note=f"真实模型调用失败，已回落到本地规则结果：{type(exc).__name__}: {exc}",
                )

        note = "未配置真实模型密钥，当前使用本地规则结果。"
        if provider and base_url and provider.api_key_hint:
            note = f"未在运行环境中找到 {provider.api_key_hint}，当前使用本地规则结果。"
        return self._mock_analyze(provider, industry_name, ocr_result, fields, rule_results, note=note)

    def _analyze_remote(
        self,
        provider: ModelProvider,
        api_key: str,
        industry_name: str,
        ocr_result: dict,
        fields: dict,
        rule_results: list[dict],
        file_path: str,
        base_url: str,
    ) -> dict:
        model_name = f"{provider.provider}/{provider.model}" if provider else "mock/local"
        supports_vision = bool(provider.supports_vision) if provider else False
        route = "vision+ocr" if supports_vision and self._is_image(file_path) else "ocr-structured-text"
        prompt = self._build_prompt(industry_name, ocr_result, fields, rule_results, route)
        content: Any = prompt
        if route == "vision+ocr":
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": self._image_data_url(file_path)}},
            ]

        payload: dict[str, Any] = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": "你是检测行业中文标签、报告和合规审核助手。"},
                {"role": "user", "content": content},
            ],
        }
        if provider.supports_json and route != "vision+ocr":
            payload["response_format"] = {"type": "json_object"}

        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        timeout = httpx.Timeout(self.timeout_seconds, connect=30)
        with httpx.Client(timeout=timeout) as client:
            data = self._post_chat_completion(
                client,
                endpoint,
                api_key,
                payload,
                provider.supports_json,
                max_attempts=2 if route == "vision+ocr" else 1,
            )

        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = self._parse_json(text)
        extracted_fields = self._extract_fields(parsed)
        findings = self._normalize_findings(parsed)
        risk_level = self._risk_level(parsed.get("risk_level"), findings, rule_results)
        confidence = self._normalize_confidence(parsed.get("confidence"))
        recognized_text = self._fields_to_text(extracted_fields) or ocr_result.get("text", "")

        return {
            "provider": model_name,
            "route": route,
            "supports_vision": supports_vision,
            "summary": parsed.get("summary") or f"已通过真实模型 {model_name} 完成{industry_name}审核。",
            "risk_level": risk_level,
            "findings": findings,
            "extracted_fields": extracted_fields,
            "label_sections": parsed.get("label_sections") if isinstance(parsed.get("label_sections"), list) else [],
            "confidence": confidence,
            "recognized_text": recognized_text,
            "unreadable_parts": self._to_string_list(parsed.get("unreadable_parts")),
            "audit_risks": self._to_string_list(parsed.get("audit_risks")),
            "model_note": "已调用 LiteLLM/OpenAI 兼容模型接口完成识别与审核。",
        }

    def _mock_analyze(
        self,
        provider: Optional[ModelProvider],
        industry_name: str,
        ocr_result: dict,
        fields: dict,
        rule_results: list[dict],
        note: str,
    ) -> dict:
        model_name = f"{provider.provider}/{provider.model}" if provider else "mock/local"
        supports_vision = bool(provider.supports_vision) if provider else False
        failed_rules = [item for item in rule_results if not item["passed"]]
        route = "vision+ocr" if supports_vision else "ocr-structured-text"
        risk_level = "low"
        if any(item["risk_level"] == "high" for item in failed_rules):
            risk_level = "high"
        elif failed_rules:
            risk_level = "medium"

        return {
            "provider": model_name,
            "route": route,
            "supports_vision": supports_vision,
            "summary": f"已基于{industry_name}规则完成审核，模型路线为 {route}。",
            "risk_level": risk_level,
            "extracted_fields": fields,
            "confidence": ocr_result.get("average_confidence", 0.91),
            "recognized_text": ocr_result.get("text", ""),
            "unreadable_parts": [],
            "audit_risks": [],
            "findings": [
                {
                    "title": item["rule_name"],
                    "risk_level": item["risk_level"],
                    "reason": item["detail"],
                    "suggestion": item["suggestion"],
                }
                for item in failed_rules
            ],
            "model_note": note,
        }

    def _resolve_api_key(self, provider: Optional[ModelProvider]) -> str:
        if not provider:
            return ""
        saved_key = (provider.api_key_secret or "").strip()
        if saved_key:
            return saved_key
        candidates = []
        hint = (provider.api_key_hint or "").strip()
        if hint:
            if self._looks_like_direct_api_key(hint):
                return hint
            candidates.append(hint.removeprefix("$"))
        normalized_provider = re.sub(r"[^A-Za-z0-9]+", "_", provider.provider or "").upper().strip("_")
        if normalized_provider:
            candidates.extend([f"{normalized_provider}_API_KEY", f"{normalized_provider}_KEY"])
        candidates.extend(["MODEL_GATEWAY_API_KEY", "OPENAI_API_KEY"])
        for name in candidates:
            value = os.getenv(name)
            if value:
                return value
        return ""

    def _resolve_base_url(self, provider: Optional[ModelProvider]) -> str:
        if provider and provider.base_url:
            return provider.base_url
        settings = get_settings()
        return settings.litellm_base_url or ""

    def _looks_like_direct_api_key(self, value: str) -> bool:
        cleaned = value.strip()
        if cleaned.startswith(("sk-", "sk_", "Bearer ")):
            return True
        return len(cleaned) >= 24 and not re.fullmatch(r"[A-Z][A-Z0-9_]*", cleaned)

    def _post_chat_completion(
        self,
        client: httpx.Client,
        endpoint: str,
        api_key: str,
        payload: dict[str, Any],
        retry_without_response_format: bool,
        max_attempts: int = 1,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        response: httpx.Response | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, max_attempts)):
            try:
                response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code < 500:
                    break
                last_error = httpx.HTTPStatusError(
                    f"Server error '{response.status_code} {response.reason_phrase}' for url '{response.url}'",
                    request=response.request,
                    response=response,
                )
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.ConnectError) as exc:
                last_error = exc
            if attempt < max_attempts - 1:
                time.sleep(1.5 * (attempt + 1))

        if response is None:
            if last_error:
                raise last_error
            raise RuntimeError("模型接口未返回响应")

        if response.status_code >= 400 and retry_without_response_format and "response_format" in payload:
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format", None)
            response = client.post(endpoint, headers=headers, json=fallback_payload)
        response.raise_for_status()
        return response.json()

    def _parse_library_remote(
        self,
        provider: ModelProvider,
        api_key: str,
        base_url: str,
        target_library: str,
        industry_name: str,
        filename: str,
        text: str,
    ) -> dict[str, Any]:
        if target_library == "quote":
            schema_instruction = (
                "输出 JSON：quote_items 数组。每个 quote_items 元素包含 code, name, method_standard, "
                "judgment_standard, sample_amount, cycle_days, price, package_name, remark。"
            )
        else:
            schema_instruction = (
                "输出 JSON：standards 数组和 rules 数组。standards 元素包含 code, name, version, "
                "effective_date, clauses；clauses 元素包含 no, title, content。rules 元素包含 "
                "standard_code, name, rule_type, field_key, trigger, risk_level, suggestion, source_excerpt。"
            )
        prompt = (
            f"你是检测行业资料入库解析助手。行业：{industry_name}。文件名：{filename}。"
            "请从文档中抽取可追溯的结构化资料，只返回 JSON，不要 Markdown。"
            "复杂或不确定内容不要编造，保留 source_excerpt 或 remark 方便人工确认。"
            f"{schema_instruction}\n\n文档正文：\n{text[:24000]}"
        )
        payload: dict[str, Any] = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": "你负责把检测行业法规、标准、报价文档解析成结构化 JSON。"},
                {"role": "user", "content": prompt},
            ],
        }
        if provider.supports_json:
            payload["response_format"] = {"type": "json_object"}
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        timeout = httpx.Timeout(self.timeout_seconds, connect=30)
        with httpx.Client(timeout=timeout) as client:
            data = self._post_chat_completion(client, endpoint, api_key, payload, provider.supports_json)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = self._parse_json(content)
        parsed["model"] = f"{provider.provider}/{provider.model}"
        parsed["model_note"] = "已调用 LiteLLM/OpenAI 兼容模型接口解析入库文件。"
        return parsed

    def _parse_library_local(self, target_library: str, industry_name: str, filename: str, text: str) -> dict[str, Any]:
        if target_library == "quote":
            return self._parse_quote_library_local(filename, text)
        return self._parse_standard_library_local(industry_name, filename, text)

    def _parse_standard_library_local(self, industry_name: str, filename: str, text: str) -> dict[str, Any]:
        code_match = re.search(r"(GB(?:/T)?\s*\d+(?:\.\d+)?(?:-\d{4})?|T/[A-Z0-9]+\s*\d+(?:-\d{4})?)", text, re.IGNORECASE)
        code = (code_match.group(1).replace(" ", "") if code_match else Path(filename).stem.upper())[:80] or "IMPORTED-STANDARD"
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clauses = []
        for line in lines[:80]:
            if len(line) < 6:
                continue
            clause_no = ""
            no_match = re.match(r"^(\d+(?:\.\d+){0,3})[\s、.．-]+(.+)$", line)
            title = line[:160]
            content = line
            if no_match:
                clause_no = no_match.group(1)
                title = no_match.group(2)[:160]
            if no_match or any(word in line for word in ["应", "不得", "标签", "标识", "营养", "许可证", "警示", "样品", "判定"]):
                clauses.append({"no": clause_no or f"摘录{len(clauses) + 1}", "title": title, "content": content})
            if len(clauses) >= 12:
                break

        rule_specs = [
            ("license_no", ["许可证", "生产许可", "SC"], "生产许可信息核验", "high"),
            ("nutrition", ["营养", "NRV", "蛋白质", "脂肪", "钠"], "营养成分标示核验", "medium"),
            ("claims", ["声称", "宣传", "不得", "功效", "治疗", "最高级"], "宣传语和禁限用表述核验", "high"),
            ("net_content", ["净含量", "规格"], "净含量标示核验", "medium"),
            ("storage_condition", ["贮存", "储存", "保存"], "贮存条件核验", "medium"),
            ("manual_warning", ["警示", "警告", "安全说明"], "警示语和安全说明核验", "high"),
        ]
        rules = []
        for field_key, keywords, name, risk_level in rule_specs:
            matched_line = next((line for line in lines if any(word in line for word in keywords)), "")
            if not matched_line:
                continue
            rules.append(
                {
                    "standard_code": code,
                    "name": name,
                    "rule_type": "ai",
                    "field_key": field_key,
                    "trigger": matched_line[:500],
                    "risk_level": risk_level,
                    "suggestion": "请按来源文件条款核验标签/资料，并在必要时补充检测或人工复核。",
                    "source_excerpt": matched_line[:700],
                }
            )
        return {
            "model": "local-library-parser",
            "standards": [
                {
                    "code": code,
                    "name": Path(filename).stem or f"{industry_name}导入标准",
                    "version": "导入文档",
                    "effective_date": "",
                    "clauses": clauses or [{"no": "导入原文", "title": text[:160], "content": text[:4000]}],
                }
            ],
            "rules": rules,
        }

    def _parse_quote_library_local(self, filename: str, text: str) -> dict[str, Any]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        items = []
        for index, line in enumerate(lines):
            if not re.search(r"(\d+(?:\.\d+)?)\s*(元|￥|rmb|RMB|CNY|¥)", line) and not re.search(r"(价格|报价|费用).{0,12}\d+", line):
                continue
            price_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|￥|rmb|RMB|CNY|¥)?", line)
            cycle_match = re.search(r"(\d+)\s*(?:个)?工作?日|周期[:：]?\s*(\d+)", line)
            code_match = re.search(r"\b([A-Z]{1,5}\d{2,6})\b", line)
            name = re.sub(r"[￥¥]?\d+(?:\.\d+)?\s*(元|rmb|RMB|CNY|¥)?", "", line)
            name = re.sub(r"\b[A-Z]{1,5}\d{2,6}\b", "", name).strip(" -—,，;；|")
            items.append(
                {
                    "code": code_match.group(1) if code_match else f"IMP{len(items) + 1:03d}",
                    "name": name[:120] or f"{Path(filename).stem}项目{len(items) + 1}",
                    "method_standard": "",
                    "judgment_standard": "",
                    "sample_amount": "按报价文件要求送样，需人工确认。",
                    "cycle_days": int(next((group for group in (cycle_match.groups() if cycle_match else []) if group), "5")),
                    "price": float(price_match.group(1)) if price_match else 0,
                    "package_name": Path(filename).stem or "导入报价库",
                    "remark": line[:700],
                }
            )
            if len(items) >= 30:
                break
        return {
            "model": "local-library-parser",
            "quote_items": items,
        }

    def _build_prompt(
        self,
        industry_name: str,
        ocr_result: dict,
        fields: dict,
        rule_results: list[dict],
        route: str,
    ) -> str:
        rules = [
            {
                "rule_name": item.get("rule_name"),
                "field_key": item.get("field_key"),
                "risk_level": item.get("risk_level"),
                "passed": item.get("passed"),
                "detail": self._truncate_text(item.get("detail"), 120),
                "suggestion": self._truncate_text(item.get("suggestion"), 160),
                "standard": item.get("standard"),
                "standard_clause": item.get("standard_clause"),
                "source_excerpt": self._truncate_text(item.get("source_excerpt"), 260),
            }
            for item in self._select_prompt_rules(rule_results)
        ]
        ocr_text = ocr_result.get("text", "")
        extracted_before_model = fields
        if route == "vision+ocr":
            extracted_before_model = {}
            if ocr_result.get("provider") in {"mock", "unavailable"}:
                ocr_text = ""
        context = {
            "industry": industry_name,
            "route": route,
            "priority": "视觉模型直接识别图片为准；OCR 仅作为参考，不作为缺失判定依据。" if route == "vision+ocr" else "OCR 结构化文本为主。",
            "ocr_text": ocr_text,
            "ocr_confidence": ocr_result.get("average_confidence"),
            "ocr_provider": ocr_result.get("provider"),
            "extracted_fields_before_model": extracted_before_model,
            "rules": rules,
        }
        return (
            "请先完整还原上传文件中的中文标签/报告事实，再按检测行业审核要求输出紧凑 JSON。"
            "如果 route=vision+ocr，你必须把图片视觉识别作为第一依据，先独立阅读图片中的标签文字、表格和版面；"
            "OCR 文本只能作为辅助参考，不能因为 OCR 漏识别、乱码或字段为空就判定标签缺失。"
            "你的处理顺序必须是：1 完整识别标签原文；2 按版面区域拆分字段；3 标记缺失/看不清/低置信度；"
            "4 再使用 rules 对已确认字段做法规审核。"
            "当图片中确实看得见某字段时，应在 extracted_fields 中补全并在 findings 中不要输出该字段缺失风险。"
            "只有图片本身也看不清、被遮挡、缺少该字段，或法规规则核验后仍不合规，才输出风险。"
            "审核依据必须优先使用审核上下文 rules 中提供的本地标准规则、条款号、source_excerpt 和 suggestion；"
            "不要假装联网检索法规，不要编造未在上下文出现的具体条款。"
            "必须只返回 JSON，不要 Markdown。JSON 字段必须包含："
            "summary, risk_level(low|medium|high), confidence(0-1), extracted_fields, label_sections, findings, "
            "audit_risks, unreadable_parts。"
            "extracted_fields 中尽量包含 product_name, product_type, net_content, shelf_life, "
            "production_date, expiry_date, license_no, manufacturer, address, phone, ingredients, additives, allergens, "
            "nutrition, nutrition_tables, claims, storage_condition, execution_standard。"
            "宠物食品还要抽取 target_pet, feeding_instruction, manual_warning；电子电器还要抽取 model_no, rating, certification, manual_warning。"
            "label_sections 是数组，每项包含 field_key, label, text, confidence(0-1), present(boolean), note。"
            "营养表可以压缩表达，字段看不清就写 null，并在 unreadable_parts 或 label_sections.note 中说明。"
            "findings 每项包含 title, risk_level, field_key, evidence_text, reason, suggestion, standard_code, standard_clause, source_excerpt。"
            "如果 OCR 不可用、OCR 低置信度或 extracted_fields_before_model 为空，请先基于图片独立识别字段。"
            "如果本地 rules 已经包含 failed 或 vision_check_required 规则，请结合你从图片识别出的字段重新判断，"
            "并保留对应 standard_code、standard_clause 和 source_excerpt。"
            f"\n\n审核上下文：{json.dumps(context, ensure_ascii=False)}"
        )

    def _parse_json(self, text: str) -> dict[str, Any]:
        if not text:
            return {}
        cleaned = text.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            cleaned = fence.group(1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        try:
            value = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"summary": text[:800], "risk_level": "medium", "audit_risks": ["模型返回内容不是标准 JSON。"]}
        return value if isinstance(value, dict) else {}

    def _extract_fields(self, parsed: dict[str, Any]) -> dict[str, Any]:
        fields = parsed.get("extracted_fields")
        if isinstance(fields, dict):
            extracted = dict(fields)
        else:
            extracted = {key: parsed.get(key) for key in FIELD_KEYS if key in parsed}

        if "claims" not in extracted and "claims_or_marketing_words" in extracted:
            extracted["claims"] = extracted["claims_or_marketing_words"]
        if "nutrition" not in extracted and "nutrition_tables" in extracted:
            extracted["nutrition"] = self._stringify(extracted["nutrition_tables"])
        return {key: value for key, value in extracted.items() if value not in (None, "", [], {})}

    def _normalize_findings(self, parsed: dict[str, Any]) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        raw_findings = parsed.get("findings")
        if isinstance(raw_findings, list):
            for item in raw_findings:
                if isinstance(item, dict):
                    findings.append(
                        {
                            "finding_id": str(item.get("finding_id") or ""),
                            "title": str(item.get("title") or "模型风险提示"),
                            "risk_level": self._normalize_risk(item.get("risk_level")),
                            "field_key": str(item.get("field_key") or ""),
                            "evidence_text": str(item.get("evidence_text") or item.get("evidence") or ""),
                            "reason": str(item.get("reason") or item.get("detail") or ""),
                            "suggestion": str(item.get("suggestion") or "建议人工复核并结合现行标准确认。"),
                            "standard_code": str(item.get("standard_code") or item.get("standard") or ""),
                            "standard_clause": str(item.get("standard_clause") or item.get("clause") or ""),
                            "source_excerpt": str(item.get("source_excerpt") or ""),
                            "confidence": str(item.get("confidence") or ""),
                            "needs_human_review": str(item.get("needs_human_review") or ""),
                            "recommended_item_codes": item.get("recommended_item_codes") if isinstance(item.get("recommended_item_codes"), list) else [],
                        }
                    )

        for risk in self._to_string_list(parsed.get("audit_risks")):
            findings.append(
                {
                    "title": "模型风险提示",
                    "risk_level": "medium",
                    "reason": risk,
                    "suggestion": "建议人工复核并结合现行标准确认。",
                }
            )

        return findings

    def _risk_level(self, raw_level: Any, findings: list[dict], rule_results: list[dict]) -> str:
        normalized = self._normalize_risk(raw_level, default="low")
        levels = [normalized]
        levels.extend(self._normalize_risk(item.get("risk_level")) for item in findings)
        levels.extend(self._normalize_risk(item.get("risk_level")) for item in rule_results if not item.get("passed"))
        if "high" in levels:
            return "high"
        if "medium" in levels:
            return "medium"
        return "low"

    def _normalize_risk(self, value: Any, default: str = "medium") -> str:
        text = str(value or "").lower()
        if text in {"high", "高", "高风险"}:
            return "high"
        if text in {"low", "低", "低风险"}:
            return "low"
        return default

    def _normalize_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.75
        if confidence > 1:
            confidence = confidence / 100
        return max(0, min(confidence, 1))

    def _image_data_url(self, file_path: str) -> str:
        path = Path(file_path)
        optimized = self._optimized_image_bytes(path)
        if optimized:
            mime, data = optimized
        else:
            mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            data = path.read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def _optimized_image_bytes(self, path: Path) -> Optional[tuple[str, bytes]]:
        try:
            from PIL import Image, ImageOps
        except Exception:
            return None

        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                elif image.mode == "L":
                    image = image.convert("RGB")

                width, height = image.size
                longest_edge = max(width, height)
                if longest_edge > self.max_vision_image_edge:
                    scale = self.max_vision_image_edge / longest_edge
                    image = image.resize((max(1, int(width * scale)), max(1, int(height * scale))))

                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=self.vision_image_quality, optimize=True)
                data = buffer.getvalue()
        except Exception:
            return None

        original_size = path.stat().st_size
        if data and len(data) < original_size * 1.25:
            return "image/jpeg", data
        if original_size > 1_000_000:
            return "image/jpeg", data
        return None

    def _select_prompt_rules(self, rule_results: list[dict]) -> list[dict]:
        failed = [item for item in rule_results if not item.get("passed")]
        high = [item for item in rule_results if item.get("risk_level") == "high" and item not in failed]
        remaining = [item for item in rule_results if item not in failed and item not in high]
        selected = [*failed, *high, *remaining]
        return selected[: self.max_rules_in_prompt]

    def _truncate_text(self, value: Any, limit: int) -> str:
        text = self._stringify(value or "")
        return text if len(text) <= limit else f"{text[:limit]}..."

    def _is_image(self, file_path: str) -> bool:
        mime = mimetypes.guess_type(file_path)[0] or ""
        return mime.startswith("image/")

    def _fields_to_text(self, fields: dict[str, Any]) -> str:
        lines = []
        for key, value in fields.items():
            lines.append(f"{key}: {self._stringify(value)}")
        return "\n".join(lines)

    def _to_string_list(self, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [self._stringify(item) for item in value if item not in (None, "")]
        return [self._stringify(value)]

    def _stringify(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)


def get_model_gateway() -> ModelGateway:
    return ModelGateway()
