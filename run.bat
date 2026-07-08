@echo off
chcp 65001 >nul
REM ==== UNIVERSITIES AFTER AI - launcher (ASCII) ====
cd /d "%~dp0"

:menu
echo.
echo ==============================================
echo   UNIVERSITIES AFTER AI  -  pipeline launcher
echo ==============================================
echo   1) Review viewer   (edit screen, browser)
echo   2) Build all chapters -^> 05-hwpx
echo   3) Export PDFs (Hancom) -^> 05-hwpx
echo   4) Merge book -^> 06-book
echo   5) Extract from PDF (new run)
echo   0) Quit
echo.
set /p sel="Select: "

if "%sel%"=="1" goto viewer
if "%sel%"=="2" goto build
if "%sel%"=="3" goto pdf
if "%sel%"=="4" goto merge
if "%sel%"=="5" goto extract
if "%sel%"=="0" goto end
echo Invalid choice.
goto menu

:viewer
echo Opening http://127.0.0.1:8770 ...
start "" "http://127.0.0.1:8770"
python run.py viewer
goto menu

:build
for /f "delims=" %%D in ('python -c "import sys;sys.path.insert(0,'pipeline');import os,paths;print(os.path.basename(paths.latest_run()))"') do set RUN=%%D
echo Run: %RUN%
for /f "delims=" %%C in ('dir /b "output\%RUN%\02-translate"') do python run.py build %%C --run "%RUN%"
goto menu

:pdf
python run.py pdf-batch
goto menu

:merge
python run.py merge
goto menu

:extract
python run.py extract
goto menu

:end
