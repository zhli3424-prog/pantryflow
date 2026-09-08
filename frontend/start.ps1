$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "node_modules")) {
    throw "未找到 frontend/node_modules，请先运行 bun install。"
}

& bun run dev
