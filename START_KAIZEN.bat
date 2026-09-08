@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo KAIZEN AI - Manufacturing Decision Intelligence V1.0.0
echo ========================================

where py >nul 2>&1
if %errorlevel%==0 (
  set PY=py
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    goto :error
  )
  set PY=python
)

if not exist .venv (
  echo [SETUP] Creating Python virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

python -c "import fastapi,numpy,scipy,pandas,statsmodels; import google.genai" >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Installing or upgrading dependencies...
  python -m pip install --upgrade pip
  if errorlevel 1 goto :error
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

echo [CHECK] Running diagnostics...
python scripts\diagnose.py
if errorlevel 1 goto :error

echo [START] Launching KAIZEN on the first available local port (9550-9589)...
python scripts\launch.py
if errorlevel 1 goto :error

exit /b 0

:error
echo.
echo ========================================
echo KAIZEN FAILED TO START

echo The window will stay open so you can copy the error above into ChatGPT.
echo ========================================
pause
exit /b 1
