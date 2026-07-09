@echo off
chcp 65001 >nul
REM ==== 영한 번역기 - initial setup (ASCII) ====
REM Installs Python deps, KoPub World fonts, and bakes the hwpx template.
cd /d "%~dp0"

echo [1/4] Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :err

echo.
echo [2/4] Installing KoPub World fonts (user font folder)...
python run.py setup-fonts
if errorlevel 1 goto :err

echo.
echo [3/4] Building master template (styles + fonts)...
python run.py template
if errorlevel 1 goto :err

echo.
echo [4/4] Checking OpenAI Codex CLI (for GPT translate/refine)...
where codex >nul 2>&1
if errorlevel 1 (
  echo   codex NOT found. Install Node.js, then:  npm i -g @openai/codex
  echo   After install, log in once:  codex login
  echo   ^(Translation/refine will be disabled until then; the rest of the pipeline still works.^)
) else (
  echo   codex found. If not logged in yet, run once:  codex login
)

echo.
echo Setup complete.  See docs\llm-codex.md for GPT login/model details.
goto :end

:err
echo.
echo Setup FAILED. See messages above.

:end
pause
