$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    Write-Host 'Run setup.ps1 first.'
    exit 1
}

if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    Write-Host 'The frontend build is missing. Run setup.ps1 first.'
    exit 1
}

Write-Host 'Newsletter Studio: http://127.0.0.1:8000'
Write-Host 'Press Ctrl+C to stop the server.'
& '.\.venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
