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
  UNIVERSITIES AFTER AI  -  pipeline launcher
==============================================
  1) New workspace from PDF         (title 입력 -> 워크스페이스 + 통째 추출)
  2) Extract THIS book (192p)       (-> 01-extract, 장별)
  3) Review viewer / GPT translate  (02-04, browser)
  4) Build chapters                 (-> 05-hwpx)
  5) Export PDFs (Hancom, Windows only)
  6) Merge book                     (-> 06-book)
  7) Quit
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
       echo "Done. Open 'Review viewer' (3) to translate/edit."
       ;;
    2) "$PY" run.py extract ;;
    3) open_url "http://127.0.0.1:8770"; "$PY" run.py viewer ;;
    4)
       RUN="$(latest_run)"
       echo "Run: ${RUN:-<none>}"
       if [ -n "$RUN" ]; then
         for d in output/*/"$RUN"/02-translate/*/; do
           [ -d "$d" ] || continue
           cid="$(basename "$d")"
           "$PY" run.py build "$cid" --run "$RUN"
         done
       fi
       ;;
    5) "$PY" run.py pdf-batch ;;
    6) "$PY" run.py merge ;;
    7) exit 0 ;;
    *) echo "Invalid choice." ;;
  esac
}

while true; do menu; done
