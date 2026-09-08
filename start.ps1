$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "backend\.venv\Scripts\python.exe") -or -not (Test-Path "frontend\node_modules")) {
    throw "Dependencies are missing. Run .\setup.ps1 first."
}

Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$PSScriptRoot\backend\start.ps1"
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$PSScriptRoot\frontend\start.ps1"

Write-Host "PantryFlow is starting:" -ForegroundColor Green
Write-Host "  App:  http://127.0.0.1:5173"
Write-Host "  API:  http://127.0.0.1:8000/docs"
Write-Host "Close the two server windows to stop the app."
