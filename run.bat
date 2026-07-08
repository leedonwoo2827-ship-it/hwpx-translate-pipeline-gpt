@echo off
chcp 65001 >nul
REM ==== pipeline launcher - just opens the web viewer (do everything on the web page) ====
cd /d "%~dp0"

echo.
echo  Starting viewer:  http://127.0.0.1:8770
echo  - On the first page: drop a PDF to create a workspace, then translate / refine / build.
echo  - Keep this window open (it shows progress logs). Press Ctrl+C here to stop.
echo.

start "" "http://127.0.0.1:8770"
python run.py viewer

echo.
echo  Viewer stopped.
echo  (PDF export via Hancom / merge to one book are CLI:  python run.py pdf-batch   /   python run.py merge)
pause
