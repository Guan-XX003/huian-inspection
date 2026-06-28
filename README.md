# 汇安检测

这是一个可本地运行的 v1 MVP：前端使用 Next.js，后端使用 FastAPI，桌面端使用 Tauri。默认 SQLite 演示数据库，系统已经接入可替换适配器：PaddleOCR OCR、MinerU/RAGFlow 文档解析预留、LiteLLM/OpenAI 兼容模型网关、多模型 API 和 Win/Mac 打包能力。

## 目录

```text
apps/
  api/       FastAPI 后端
  web/       Next.js 前端
  desktop/   Tauri 桌面端
scripts/     本地启动脚本
docs/    架构与实施说明
```

## 快速启动

### 桌面端

```bash
pnpm desktop:app
```

这个命令会自动启动本地后端、本地 UI 和 Tauri 桌面窗口。正常试用时只看桌面窗口即可，不需要手动打开浏览器。

注意：桌面窗口依赖 Tauri，需要本机安装 Rust/Cargo。缺少 `cargo` 时，命令会用中文提示安装要求。

### 开发调试

```bash
pnpm api:dev
pnpm web:dev
pnpm desktop:dev
```

开发调试时也可以访问：

- API 文档：http://localhost:8000/docs
- Web 调试页：http://localhost:3000

## v1 能力

- 工作台：文件上传、自动分类、OCR 状态、模型路由、风险报告、推荐项目、自动报价。
- 项目报价库：导入报价文档，维护解析出的报价条目。
- 设置：模型设置、知识库设置、OCR/文档解析/模型网关状态。
- 智能审核：规则引擎优先，模型分析补充；无视觉模型自动使用 OCR 结构化结果。
- 智能报价：从审核风险推荐检测项目、推荐实验室、生成报价单，并支持 PDF/Excel 下载。
- 可替换适配器：PaddleOCR 优先，缺依赖自动降级；文档解析支持 MinerU Markdown、本地 PDF/Word 解析和后续 RAGFlow；模型网关支持 LiteLLM/OpenAI 兼容接口。

## 接入真实模型

后台“模型配置”支持 OpenAI 兼容接口。以 TokensKingdom 的 `gpt-5.5` 为例：

- Base URL：`https://api.tokenskingdom.com/v1`
- 模型 ID：`gpt-5.5`
- 密钥变量名：`TOKENSKINGDOM_API_KEY`
- 能力：勾选“支持视觉”和“支持 JSON”

真实密钥放到 `apps/api/.env` 或启动环境变量里，不要填进前端列表。配置了视觉模型时，图片会以“图片 + OCR 文本”发送；配置 DeepSeek 等无视觉模型时，系统会只发送 OCR 后的结构化文本。

## 增强集成

轻量 PDF/Word 解析依赖已在后端主依赖中。PaddleOCR、LiteLLM Python 包等重型依赖放在：

```bash
apps/api/requirements-optional.txt
```

更多集成说明见：

- `docs/INTEGRATIONS.md`
- `docs/ARCHITECTURE.md`
