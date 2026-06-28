import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiDir = path.join(rootDir, "apps", "api");
const userHome = process.env.HOME ?? process.env.USERPROFILE ?? "";
const cargoBin = path.join(userHome, ".cargo", "bin");
const processes = [];

function command(name) {
  return process.platform === "win32" ? `${name}.cmd` : name;
}

function pythonCommand() {
  const venv = process.platform === "win32"
    ? path.join(apiDir, ".venv", "Scripts", "python.exe")
    : path.join(apiDir, ".venv", "bin", "python");
  if (existsSync(venv)) return venv;
  return findExecutable("python3") ?? findExecutable("python") ?? findExecutable("py") ?? venv;
}

function findExecutable(name) {
  const suffixes = process.platform === "win32" ? [".exe", ".cmd", ".bat", ""] : [""];
  const paths = [cargoBin, ...(process.env.PATH ?? "").split(path.delimiter)];
  for (const dir of paths) {
    for (const suffix of suffixes) {
      const candidate = path.join(dir, `${name}${suffix}`);
      if (existsSync(candidate)) return candidate;
    }
  }
  return null;
}

function startProcess(label, cmd, args, options = {}) {
  const child = spawn(cmd, args, {
    cwd: options.cwd ?? rootDir,
    env: {
      ...process.env,
      PATH: [cargoBin, process.env.PATH].filter(Boolean).join(path.delimiter),
      PYTHONUNBUFFERED: "1",
      NEXT_PUBLIC_API_BASE: "http://127.0.0.1:8000",
      ...options.env,
    },
    stdio: "inherit",
    shell: false,
  });

  processes.push(child);
  child.on("exit", (code) => {
    if (!shuttingDown && code !== 0) {
      console.error(`[${label}] exited with code ${code}`);
      shutdown(code ?? 1);
    }
  });
  return child;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function isReady(url) {
  try {
    const response = await fetch(url);
    return response.ok;
  } catch {
    return false;
  }
}

async function waitFor(url, label) {
  const started = Date.now();
  while (Date.now() - started < 60_000) {
    if (await isReady(url)) return;
    await wait(800);
  }
  throw new Error(`${label} did not become ready: ${url}`);
}

async function ensureService(label, url, starter) {
  if (await isReady(url)) {
    console.log(`[${label}] reusing existing service at ${url}`);
    return;
  }
  starter();
  await waitFor(url, label);
}

let shuttingDown = false;
function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of processes.reverse()) {
    if (!child.killed) child.kill("SIGTERM");
  }
  setTimeout(() => process.exit(code), 300);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

async function main() {
  const python = pythonCommand();
  if (!existsSync(python) && !findExecutable(path.basename(python))) {
    console.error([
      "没有检测到可用 Python。",
      "Windows 建议先执行：powershell -ExecutionPolicy Bypass -File scripts/windows-setup.ps1",
      "或者手动创建 apps/api/.venv 后安装后端依赖。",
    ].join("\n"));
    shutdown(1);
    return;
  }

  if (!findExecutable("cargo")) {
    console.error([
      "桌面壳需要 Rust/Cargo 才能启动 Tauri。",
      "当前电脑还没有检测到 cargo，所以前后端源码可以运行，但桌面窗口无法启动。",
      "安装 Rust 后重新执行：pnpm desktop:app",
      "官方下载地址：https://www.rust-lang.org/tools/install",
    ].join("\n"));
    shutdown(1);
    return;
  }

  await ensureService(
    "api",
    "http://127.0.0.1:8000/api/health",
    () => startProcess(
      "api",
      python,
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
      { cwd: apiDir },
    ),
  );

  await ensureService(
    "web",
    "http://127.0.0.1:3000",
    () => startProcess("web", command("pnpm"), ["--dir", "apps/web", "dev", "--hostname", "127.0.0.1"]),
  );

  startProcess("desktop", command("pnpm"), ["--dir", "apps/desktop", "tauri", "dev", "--no-watch"]);
}

main().catch((error) => {
  console.error(error);
  shutdown(1);
});
