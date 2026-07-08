@echo off
chcp 65001 >nul
REM ==== UNIVERSITIES AFTER AI - launcher (ASCII) ====
cd /d "%~dp0"

:menu
echo.
echo ==============================================
echo   pipeline launcher
echo ==============================================
echo   1) Scan a PDF    -^> new workspace (extract)
echo   2) Open viewer   (translate / refine / edit / build)
echo.
echo   3) Extract THIS book (192p, per chapter)
echo   4) Export PDFs (Hancom)    5) Merge book    6) Quit
echo.
set /p sel="Select: "

if "%sel%"=="1" goto newws
if "%sel%"=="2" goto viewer
if "%sel%"=="3" goto extract
if "%sel%"=="4" goto pdf
if "%sel%"=="5" goto merge
if "%sel%"=="6" goto end
echo Invalid choice.
goto menu

:newws
set "title="
set /p title="Book title (workspace name): "
if "%title%"=="" ( echo Title required. & goto menu )
set "pdfpath="
set /p pdfpath="PDF path (drag the file here, then Enter): "
set pdfpath=%pdfpath:"=%
if "%pdfpath%"=="" ( echo PDF path required. & goto menu )
python run.py extract --pdf "%pdfpath%" --whole --book "%title%"
echo.
echo Done. Open 'Review viewer' (3) to translate/edit.
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
