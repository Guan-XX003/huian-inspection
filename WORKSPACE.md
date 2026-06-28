# 桌面应用工作区说明

这个工作区已经按“前端 + 后端 + 桌面壳”整理：

```text
apps/
  api/      FastAPI 后端，负责审核、报价、报告、配置数据
  web/      Next.js 前端界面，桌面端直接复用这一套 UI
  desktop/  Tauri 桌面壳，负责 Win/Mac 窗口、文件选择、后续打包
scripts/
  desktop-dev.mjs  本地桌面开发启动器
docs/
  ARCHITECTURE.md  架构说明
```

## 日常启动

```bash
pnpm desktop:app
```

这个命令会自动启动：

- 本地后端：`http://127.0.0.1:8000`
- 本地前端：`http://127.0.0.1:3000`
- 桌面窗口：Tauri App

使用时只看桌面窗口即可，不需要手动打开浏览器。

桌面壳依赖 Tauri，因此本机需要安装 Rust/Cargo。若执行时提示缺少 `cargo`，先安装 Rust：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Windows 开发机建议按 Tauri 官方说明安装 Rust、WebView2 和 Visual Studio Build Tools。

## 单独调试

```bash
pnpm api:dev
pnpm web:dev
pnpm desktop:dev
```

单独调试只适合开发人员排查问题。正常演示或业务试用优先用 `pnpm desktop:app`。

## 正式打包建议

v1 可以分两种路线：

1. 局域网/云端后端：桌面端只打包 UI，连接公司后端服务。
2. 本地一体化后端：把 FastAPI 打成 Tauri sidecar，桌面端启动时自动拉起本机 API。

当前工作区已经为第二种路线预留了目录结构。正式打包前，需要把 Python 后端冻结成可执行文件，并配置到 `apps/desktop/src-tauri/tauri.conf.json` 的 sidecar 列表。
