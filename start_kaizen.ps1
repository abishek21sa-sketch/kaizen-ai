$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

try {
    Write-Host "KAIZEN AI - Manufacturing Decision Intelligence V1.0.0"
    if (-not (Test-Path ".venv")) {
        Write-Host "[SETUP] Creating Python virtual environment..."
        if (Get-Command py -ErrorAction SilentlyContinue) {
            py -m venv .venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            python -m venv .venv
        } else {
            throw "Python was not found on PATH."
        }
    }

    & .\.venv\Scripts\python.exe -c "import fastapi,numpy,scipy,pandas,statsmodels; import google.genai"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[SETUP] Installing or upgrading dependencies..."
        & .\.venv\Scripts\python.exe -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
        & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }
    }

    Write-Host "[CHECK] Running diagnostics..."
    & .\.venv\Scripts\python.exe scripts\diagnose.py
    if ($LASTEXITCODE -ne 0) { throw "diagnostics failed" }

    Write-Host "[START] Launching KAIZEN on the first available local port (9550-9589)..."
    & .\.venv\Scripts\python.exe scripts\launch.py
    if ($LASTEXITCODE -ne 0) { throw "launcher exited with code $LASTEXITCODE" }
}
catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "KAIZEN FAILED TO START" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "The window will stay open so you can copy this error into ChatGPT." -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
