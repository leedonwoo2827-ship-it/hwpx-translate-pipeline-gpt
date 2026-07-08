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
  1) Review viewer   (edit screen, browser)
  2) Build all chapters -> 05-hwpx
  3) Export PDFs (Hancom, Windows only)
  4) Merge book -> 06-book
  5) Extract from PDF (new run)
  0) Quit
EOF
  read -rp "Select: " sel
  case "$sel" in
    1) open_url "http://127.0.0.1:8770"; "$PY" run.py viewer ;;
    2)
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
    3) "$PY" run.py pdf-batch ;;
    4) "$PY" run.py merge ;;
    5) "$PY" run.py extract ;;
    0) exit 0 ;;
    *) echo "Invalid choice." ;;
  esac
}

while true; do menu; done
