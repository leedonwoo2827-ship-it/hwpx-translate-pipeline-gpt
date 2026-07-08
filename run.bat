@echo off
chcp 65001 >nul
REM ==== UNIVERSITIES AFTER AI - launcher (ASCII) ====
cd /d "%~dp0"

:menu
echo.
echo ==============================================
echo   UNIVERSITIES AFTER AI  -  pipeline launcher
echo ==============================================
echo   1) Extract from PDF               (-^> 01-extract, new run)
echo   2) Review viewer / GPT translate  (02-04, browser)
echo   3) Build chapters                 (-^> 05-hwpx)
echo   4) Export PDFs (Hancom)           (-^> PDF)
echo   5) Merge book                     (-^> 06-book)
echo   6) Quit
echo.
set /p sel="Select: "

if "%sel%"=="1" goto extract
if "%sel%"=="2" goto viewer
if "%sel%"=="3" goto build
if "%sel%"=="4" goto pdf
if "%sel%"=="5" goto merge
if "%sel%"=="6" goto end
echo Invalid choice.
goto menu

:viewer
echo Opening http://127.0.0.1:8770 ...
start "" "http://127.0.0.1:8770"
python run.py viewer
goto menu

:build
for /f "delims=" %%D in ('python -c "import sys;sys.path.insert(0,'pipeline');import paths;print(paths.latest_run() or '')"') do set "RUN=%%D"
if "%RUN%"=="" ( echo No run found. Run Extract first. & goto menu )
echo Run: %RUN%
for /f "delims=" %%C in ('dir /b "%RUN%\02-translate" 2^>nul') do python run.py build %%C --run "%RUN%"
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
