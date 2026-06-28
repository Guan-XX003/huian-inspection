param(
  [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiDir = Join-Path $Root "apps\api"
$VenvPython = Join-Path $ApiDir ".venv\Scripts\python.exe"

function Find-Python {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return $python.Source }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return $py.Source }
  throw "未检测到 Python。请先安装 Python 3.10+，并勾选 Add Python to PATH。"
}

function Run-Step($Name, [scriptblock]$Block) {
  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  & $Block
}

Run-Step "创建后端 Python 虚拟环境" {
  if (!(Test-Path $VenvPython)) {
    $Python = Find-Python
    & $Python -m venv (Join-Path $ApiDir ".venv")
  }
}

Run-Step "安装后端依赖和 Windows OCR 依赖" {
  & $VenvPython -m pip install --upgrade pip
  & $VenvPython -m pip install -r (Join-Path $ApiDir "requirements.txt") -r (Join-Path $ApiDir "requirements-windows.txt")
}

if (!$SkipPlaywright) {
  Run-Step "安装报告导出所需 Chromium" {
    & $VenvPython -m playwright install chromium
  }
}

Run-Step "安装前端和桌面依赖" {
  $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
  if (!$pnpm) {
    throw "未检测到 pnpm。请先安装 Node.js，然后执行：corepack enable && corepack prepare pnpm@latest --activate"
  }
  Push-Location $Root
  try {
    pnpm install
  } finally {
    Pop-Location
  }
}

Write-Host ""
Write-Host "Windows 环境准备完成。" -ForegroundColor Green
Write-Host "开发启动：pnpm desktop:app"
Write-Host "如需桌面窗口，请先安装 Rust/Cargo：https://www.rust-lang.org/tools/install"
