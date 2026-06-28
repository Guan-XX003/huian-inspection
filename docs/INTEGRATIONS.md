# 集成方案 v1

本项目不直接 fork 大型开源系统，而是在当前 `Next.js + FastAPI + Tauri` 主应用里接入可替换适配器。

## OCR：PaddleOCR

后端入口：`apps/api/app/services/ocr.py`

默认配置：

```env
OCR_PROVIDER=auto
```

运行逻辑：

1. TXT/CSV 直接读取文本。
2. 图片文件优先尝试 `PaddleOCR`。
3. 未安装 PaddleOCR 或识别失败时，自动降级到本地演示 OCR，保证应用仍可启动和测试。

安装建议：

```bash
cd apps/api
.venv/bin/pip install -r requirements-optional.txt
```

`paddlepaddle` 需要按目标机器 CPU/GPU 和系统版本选择官方 wheel，建议部署时单独安装。

## 文档解析：MinerU / RAGFlow 预留

后端入口：`apps/api/app/services/document_parser.py`

默认配置：

```env
DOCUMENT_PARSER_PROVIDER=auto
```

运行逻辑：

1. 若导入文件旁存在 MinerU 生成的 Markdown，会优先读取。
2. 否则本地解析 TXT/CSV/DOCX/PDF。
3. 无法结构化解析的复杂 PDF/Word 会作为原文文档保存，并标记为“需人工确认”。

后续接 RAGFlow 时，建议把标准库导入改成：

```text
上传文件 -> RAGFlow/MinerU 解析 -> 切分条款 -> 生成 Standard/AuditRule -> 人工确认 -> 启用规则
```

## 模型网关：LiteLLM/OpenAI 兼容

后端入口：`apps/api/app/services/model_gateway.py`

支持两种模式：

1. 模型配置里填写 `Base URL`，后端直接调用该 OpenAI 兼容地址。
2. 设置全局 `LITELLM_BASE_URL`，把请求统一转给 LiteLLM Proxy。

示例：

```env
MODEL_PROVIDER=litellm-compatible
LITELLM_BASE_URL=http://127.0.0.1:4000/v1
```

无视觉模型仍可工作：系统会先走 OCR，把结构化字段、OCR 文本和规则上下文发给模型。

## 审核流程：VendorAuditAI 思路

当前实现链路：

```text
上传文件
-> OCR/文档解析
-> 自动分类
-> 字段抽取
-> 标准规则库路由
-> 确定性规则审核
-> 模型补充语义风险
-> 风险详情归一化
-> 推荐检测项目
-> 自动生成报价
```

风险详情必须包含：

- 风险标题
- 风险等级
- 证据原文
- 原因
- 引用标准和条款
- 标准片段
- 整改建议
- 推荐项目
- 是否建议人工复核

## 报价/实验室对象：open-lims 思路

当前报价条目会保存：

- 检测项目
- 检测标准
- 判定标准
- 样品要求
- 周期
- 单价
- 推荐实验室
- 实验室资质
- 服务备注

报价仍以审核报告为中心：审核报告详情中可以查看报价清单，并下载 PDF/Excel。

## 桌面端：Tauri

启动：

```bash
pnpm desktop:app
```

打包：

```bash
pnpm desktop:build
```

桌面端只封装 UI 和本地文件能力，业务数据仍连接 FastAPI 后端，避免多台电脑数据不一致。
