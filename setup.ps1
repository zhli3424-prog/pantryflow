$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "需要 Python 3.12+，请先安装 Python。"
}
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    throw "需要 Bun，请先访问 https://bun.sh 安装。"
}

if (-not (Test-Path "backend\.venv\Scripts\python.exe")) {
    py -3.12 -m venv "backend\.venv"
}
& "backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements-dev.txt"

Push-Location frontend
try { bun install --frozen-lockfile } finally { Pop-Location }

if (-not (Test-Path "backend\.env")) { Copy-Item "backend\.env.example" "backend\.env" }
if (-not (Test-Path "frontend\.env")) { Copy-Item "frontend\.env.example" "frontend\.env" }

Write-Host "Setup complete. Run .\start.ps1 to launch PantryFlow." -ForegroundColor Green
