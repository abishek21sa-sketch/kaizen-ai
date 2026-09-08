$ErrorActionPreference = "Stop"
Write-Host "KAIZEN AI Enterprise Acceptance"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
if (-not (Test-Path ".venv\Scripts\python.exe")) { py -3 -m venv .venv }
$python = ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install -r requirements-dev.txt
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$g1=@("tests/test_active.py","tests/test_ai.py","tests/test_api.py","tests/test_arena.py","tests/test_cape.py","tests/test_cape_governance.py","tests/test_cape_governance_api.py","tests/test_ie.py")
$g2=@("tests/test_investigator.py","tests/test_launcher.py","tests/test_optimizer.py","tests/test_quality.py","tests/test_simulation.py","tests/test_simulator.py","tests/test_v1.py")
& $python -m pytest -q @g1
if ($LASTEXITCODE -ne 0) { throw "KAIZEN regression group 1 failed" }
& $python -m pytest -q @g2
if ($LASTEXITCODE -ne 0) { throw "KAIZEN regression group 2 failed" }
& $python scripts/portfolio_validation.py
if ($LASTEXITCODE -ne 0) { throw "KAIZEN portfolio validation failed" }
& $python scripts/enterprise_operability.py
if ($LASTEXITCODE -ne 0) { throw "KAIZEN enterprise operability failed" }
Write-Host "KAIZEN_AI_ENTERPRISE_ACCEPTANCE=PASS"
