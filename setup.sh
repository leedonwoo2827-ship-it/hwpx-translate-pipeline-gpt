#!/usr/bin/env bash
# ==== UNIVERSITIES AFTER AI - initial setup (macOS/Linux) ====
# Installs Python deps, KoPub World fonts, and bakes the hwpx template.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

echo "[1/3] Installing Python dependencies..."
"$PY" -m pip install -r requirements.txt

echo
echo "[2/3] Installing KoPub World fonts (user font folder)..."
"$PY" run.py setup-fonts

echo
echo "[3/3] Building master template (styles + fonts)..."
"$PY" run.py template

echo
echo "Setup complete."
echo "Note: hwpx->PDF export needs Hancom Office (Windows only)."
echo "      On macOS/Linux use the viewer + 'run.py build/merge'; export PDFs from Hangul manually."
