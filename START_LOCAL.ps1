$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Virtual environment .venv was not found.' -ForegroundColor Red
    Write-Host 'Install Python 3.13, then run:'
    Write-Host '  py -3.13 -m venv .venv'
    Write-Host '  .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}
Write-Host 'Starting SIMBA Portal in local demo mode...' -ForegroundColor Cyan
Write-Host 'Login URL: http://127.0.0.1:5000/login' -ForegroundColor Green
Write-Host 'Demo username: simba-demo'
Write-Host 'Demo password: SimbaDemo2026!'
& '.\.venv\Scripts\python.exe' -m flask --app wsgi run --host 127.0.0.1 --port 5000
