#!/usr/bin/env bash
# ==== UNIVERSITIES AFTER AI - launcher (macOS/Linux) ====
set -uo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

open_url() {  # cross-platform "open in browser"
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then open "$1" >/dev/null 2>&1 &
  fi
}

latest_run() {
  "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, "pipeline")
import paths
r = paths.latest_run()
print(os.path.basename(r) if r else "")
PYEOF
}

menu() {
  cat <<'EOF'

==============================================
  pipeline launcher
==============================================
  1) Scan a PDF    -> new workspace (extract)
  2) Open viewer   (translate / refine / edit / build)

  3) Extract THIS book (192p, per chapter)
  4) Export PDFs (Hancom)    5) Merge book    6) Quit
EOF
  read -rp "Select: " sel
  case "$sel" in
    1)
       read -rp "Book title (workspace name): " title
       [ -z "$title" ] && { echo "Title required."; return; }
       read -rp "PDF path: " pdfpath
       pdfpath="${pdfpath%\"}"; pdfpath="${pdfpath#\"}"   # strip quotes
       [ -z "$pdfpath" ] && { echo "PDF path required."; return; }
       "$PY" run.py extract --pdf "$pdfpath" --whole --book "$title"
       echo "Done. Open viewer (2) to translate/edit."
       ;;
    2) open_url "http://127.0.0.1:8770"; "$PY" run.py viewer ;;
    3) "$PY" run.py extract ;;
    4) "$PY" run.py pdf-batch ;;
    5) "$PY" run.py merge ;;
    6) exit 0 ;;
    *) echo "Invalid choice." ;;
  esac
}

while true; do menu; done
