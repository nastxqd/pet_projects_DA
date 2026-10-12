$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
Write-Host 'Starting Lingua Lab at http://localhost:8000' -ForegroundColor Cyan
python app.py
