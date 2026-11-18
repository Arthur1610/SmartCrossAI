@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3, 11))"
if errorlevel 1 (
    echo Instale o Python 3.11 ou superior e recrie o ambiente virtual.
    exit /b 1
)
if /i "%~1"=="--simulacao" (
    ".venv\Scripts\python.exe" -m pip install -r requirements-core.txt
    exit /b
)
".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
exit /b
