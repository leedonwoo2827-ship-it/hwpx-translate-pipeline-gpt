@echo off
chcp 65001 >nul
REM ==== UNIVERSITIES AFTER AI - initial setup (ASCII) ====
REM Installs Python deps, KoPub World fonts, and bakes the hwpx template.
cd /d "%~dp0"

echo [1/3] Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :err

echo.
echo [2/3] Installing KoPub World fonts (user font folder)...
python run.py setup-fonts
if errorlevel 1 goto :err

echo.
echo [3/3] Building master template (styles + fonts)...
python run.py template
if errorlevel 1 goto :err

echo.
echo Setup complete.
goto :end

:err
echo.
echo Setup FAILED. See messages above.

:end
pause
