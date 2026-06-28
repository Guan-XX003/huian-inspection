from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Industry, ModelProvider, UploadedFile
from app.services.industry_router import classify_industry_code
from app.services.model_gateway import ModelGateway


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_industry_router_maps_core_categories() -> None:
    examples = {
        "pet_food": "全价犬粮 宠物饲料 成分分析保证值 粗蛋白 粗脂肪",
        "electronics": "产品型号 ABC-01 额定输入 220V CCC 电磁兼容 EMC",
        "dairy": "发酵乳 生牛乳 蛋白质 乳酸菌 冷藏保存",
        "canned_food": "午餐肉罐头 商业无菌 常温保存",
        "frozen_food": "速冻水饺 -18℃ 以下冷冻保存",
        "puffed_food": "膨化食品 薯片 酸价 过氧化值",
        "candy": "凝胶糖果 代可可脂巧克力 甜味剂",
        "food": "预包装食品 配料 净含量 营养成分 保质期",
    }
    for expected, text in examples.items():
        assert classify_industry_code(text) == expected


def test_audit_uses_model_extracted_fields(monkeypatch, tmp_path) -> None:
    def fake_analyze(self, provider, industry_name, ocr_result, fields, rule_results, file_path):
        return {
            "provider": "test/gpt-5.5",
            "route": "vision+ocr",
            "supports_vision": True,
            "summary": "真实模型识别完成。",
            "risk_level": "low",
            "findings": [],
            "extracted_fields": {
                "product_name": "烧凉粉（方便凉粉）",
                "license_no": "SC10741018302531",
                "nutrition": "能量、蛋白质、脂肪、碳水化合物、钠",
                "claims": "方便凉粉",
            },
            "confidence": 0.88,
            "recognized_text": "产品名称：烧凉粉（方便凉粉）\n食品生产许可证编号：SC10741018302531",
            "unreadable_parts": [],
            "audit_risks": [],
            "model_note": "test",
        }

    monkeypatch.setattr(ModelGateway, "analyze", fake_analyze)

    client = TestClient(app)
    client.get("/api/health")
    image_path = tmp_path / "label.jpg"
    image_path.write_bytes(b"fake image bytes")

    with SessionLocal() as db:
        industry = db.query(Industry).filter(Industry.code == "food").first()
        assert industry is not None
        provider = db.query(ModelProvider).filter(ModelProvider.supports_vision.is_(True)).first()
        if provider is None:
            provider = ModelProvider(
                provider="test-provider",
                model="vision-model",
                base_url="https://example.test/v1",
                api_key_hint="TEST_MODEL_API_KEY",
                supports_vision=True,
                supports_json=True,
            )
            db.add(provider)
        file = UploadedFile(original_name="label.jpg", path=str(image_path), content_type="image/jpeg", size=16)
        db.add(file)
        db.commit()
        db.refresh(provider)
        db.refresh(file)

        response = client.post(
            "/api/audit/tasks",
            json={
                "industry_id": industry.id,
                "file_id": file.id,
                "customer_name": "测试客户",
                "document_type": "产品标签",
                "model_provider_id": provider.id,
            },
        )

    assert response.status_code == 200
    task = response.json()
    assert task["extracted_fields"]["product_name"] == "烧凉粉（方便凉粉）"
    assert task["extracted_fields"]["license_no"] == "SC10741018302531"
    assert task["model_used"] == "test/gpt-5.5"
    assert task["final_report"]["route"] == "vision+ocr"


def test_standard_document_import_creates_reviewable_rules(monkeypatch, tmp_path) -> None:
    def fake_parse_library_document(self, provider, target_library, industry_name, filename, text):
        assert target_library == "standard_rule"
        return {
            "model": "test/parser",
            "model_note": "test",
            "standards": [
                {
                    "code": "GB 7718-2011",
                    "name": "食品安全国家标准 预包装食品标签通则",
                    "version": "2011",
                    "effective_date": "",
                    "clauses": [{"no": "4.1", "title": "标签内容", "content": "预包装食品标签应清晰、醒目。"}],
                }
            ],
            "rules": [
                {
                    "standard_code": "GB 7718-2011",
                    "name": "标签清晰度核验",
                    "rule_type": "ai",
                    "field_key": "claims",
                    "trigger": "预包装食品标签应清晰、醒目。",
                    "risk_level": "medium",
                    "suggestion": "请人工确认标签可读性。",
                    "source_excerpt": "预包装食品标签应清晰、醒目。",
                }
            ],
        }

    monkeypatch.setattr(ModelGateway, "parse_library_document", fake_parse_library_document)

    client = TestClient(app)
    client.get("/api/health")
    with SessionLocal() as db:
        industry = db.query(Industry).filter(Industry.code == "food").first()
        assert industry is not None
        industry_id = industry.id

    response = client.post(
        "/api/admin/standard-rule-library/import",
        data={"industry_id": industry_id},
        files={"file": ("gb7718.txt", b"GB 7718-2011\n4.1 label", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["standards_created"] in {0, 1}
    assert payload["rules_created"] == 1
    assert payload["clause_chunks_created"] >= 1
    assert payload["import_task"]["status"] == "needs_review"
    assert payload["import_task"]["parsed_result"]["model"] == "test/parser"

    rules = client.get("/api/admin/audit-rules").json()
    assert any(rule["name"] == "标签清晰度核验" for rule in rules)


def test_quote_document_import_creates_quote_items(monkeypatch) -> None:
    def fake_parse_library_document(self, provider, target_library, industry_name, filename, text):
        assert target_library == "quote"
        return {
            "model": "test/parser",
            "quote_items": [
                {
                    "code": "QX001",
                    "name": "标签合规审核",
                    "method_standard": "GB 7718-2011",
                    "judgment_standard": "GB 7718-2011",
                    "sample_amount": "标签照片或包装样 1 份",
                    "cycle_days": 3,
                    "price": 500,
                    "package_name": "导入报价库",
                }
            ],
        }

    monkeypatch.setattr(ModelGateway, "parse_library_document", fake_parse_library_document)

    client = TestClient(app)
    client.get("/api/health")
    with SessionLocal() as db:
        industry = db.query(Industry).filter(Industry.code == "food").first()
        assert industry is not None
        industry_id = industry.id

    response = client.post(
        "/api/admin/quote-library/import",
        data={"industry_id": industry_id},
        files={"file": ("quote.txt", b"label review 500 yuan", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items_created"] == 1
    assert payload["import_task"]["status"] == "needs_review"

    items = client.get("/api/admin/detection-items").json()
    assert any(item["code"] == "QX001" and item["name"] == "标签合规审核" for item in items)
