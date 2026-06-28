import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiDir = path.join(rootDir, "apps", "api");
const separator = process.platform === "win32" ? ";" : ":";
const python = process.platform === "win32"
  ? path.join(apiDir, ".venv", "Scripts", "python.exe")
  : path.join(apiDir, ".venv", "bin", "python");

if (!existsSync(python)) {
  console.error(`没有找到后端 Python 环境：${python}`);
  console.error("请先运行 Windows 环境准备脚本，或在 apps/api 下创建 .venv 并安装依赖。");
  process.exit(1);
}

const addData = (source, target) => `${source}${separator}${target}`;
const args = [
  "-m",
  "PyInstaller",
  "--noconfirm",
  "--clean",
  "--onedir",
  "--name",
  "huian-api",
  "desktop_server.py",
  "--add-data",
  addData("app/seed/inspection_ai_seed.db", "app/seed"),
  "--add-data",
  addData("app/seed/builtin_official_pack", "app/seed/builtin_official_pack"),
  "--add-data",
  addData("app/seed/builtin_legal_pack", "app/seed/builtin_legal_pack"),
  "--add-data",
  addData("app/reports", "app/reports"),
  "--add-data",
  addData("app/storage", "app/storage"),
  "--hidden-import",
  "app.main",
  "--hidden-import",
  "app.routers.admin",
  "--hidden-import",
  "app.routers.audit",
  "--hidden-import",
  "app.routers.files",
  "--hidden-import",
  "app.routers.quotes",
  "--hidden-import",
  "app.routers.reports",
  "--hidden-import",
  "pypdf",
  "--hidden-import",
  "fitz",
  "--hidden-import",
  "docx",
  "--hidden-import",
  "rapidocr_onnxruntime",
  "--collect-all",
  "rapidocr_onnxruntime",
  "--collect-all",
  "onnxruntime",
];

const result = spawnSync(python, args, {
  cwd: apiDir,
  stdio: "inherit",
  shell: false,
});

process.exit(result.status ?? 1);
