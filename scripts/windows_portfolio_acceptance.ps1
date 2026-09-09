$ErrorActionPreference = "Stop"
Write-Host "KAIZEN AI Portfolio release Acceptance"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
if (-not (Test-Path ".venv\Scripts\python.exe")) { py -3 -m venv .venv }
$python = ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install -r requirements-dev.txt
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
& $python -m pytest -q
& $python scripts/portfolio_validation.py
Write-Host "KAIZEN_AI_PORTFOLIO_RELEASE_ACCEPTANCE=PASS"
