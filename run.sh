#!/usr/bin/env bash
# ==== pipeline launcher - just opens the web viewer (do everything on the web page) ====
set -uo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

open_url() {
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then open "$1" >/dev/null 2>&1 &
  fi
}

echo
echo " Starting viewer:  http://127.0.0.1:8770"
echo " - On the first page: drop a PDF to create a workspace, then translate / refine / build."
echo " - Keep this window open (progress logs). Ctrl+C to stop."
echo
echo " (PDF export via Hancom is Windows-only; merge:  python run.py merge)"
echo

open_url "http://127.0.0.1:8770"
"$PY" run.py viewer
