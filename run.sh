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
  1) Extract from PDF               (-> 01-extract, new run)
  2) Review viewer / GPT translate  (02-04, browser)
  3) Build chapters                 (-> 05-hwpx)
  4) Export PDFs (Hancom, Windows only)
  5) Merge book                     (-> 06-book)
  6) Quit
EOF
  read -rp "Select: " sel
  case "$sel" in
    1) "$PY" run.py extract ;;
    2) open_url "http://127.0.0.1:8770"; "$PY" run.py viewer ;;
    3)
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
    4) "$PY" run.py pdf-batch ;;
    5) "$PY" run.py merge ;;
    6) exit 0 ;;
    *) echo "Invalid choice." ;;
  esac
}

while true; do menu; done
