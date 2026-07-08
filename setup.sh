#!/usr/bin/env bash
# ==== UNIVERSITIES AFTER AI - initial setup (macOS/Linux) ====
# Installs Python deps, KoPub World fonts, and bakes the hwpx template.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

echo "[1/4] Installing Python dependencies..."
"$PY" -m pip install -r requirements.txt

echo
echo "[2/4] Installing KoPub World fonts (user font folder)..."
"$PY" run.py setup-fonts

echo
echo "[3/4] Building master template (styles + fonts)..."
"$PY" run.py template

echo
echo "[4/4] Checking OpenAI Codex CLI (for GPT translate/refine)..."
if command -v codex >/dev/null 2>&1; then
  echo "  codex found. If not logged in yet, run once:  codex login"
else
  echo "  codex NOT found. Install Node.js, then:  npm i -g @openai/codex"
  echo "  After install, log in once:  codex login"
  echo "  (Translation/refine will be disabled until then; the rest of the pipeline still works.)"
fi

echo
echo "Setup complete.  See docs/llm-codex.md for GPT login/model details."
echo "Note: hwpx->PDF export needs Hancom Office (Windows only)."
echo "      On macOS/Linux use the viewer + 'run.py build/merge'; export PDFs from Hangul manually."
