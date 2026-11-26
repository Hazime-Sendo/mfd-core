#!/usr/bin/env bash
# Records, for several interpreter modes, (a) the unittest result and (b) the exit status of the WHOLE process, with stderr.
# Purpose: separate "tests passed" from "process ended normally". Does not change any result. Usage: bash tools/strict_mode_diagnostics.sh [python] [outfile]
PY="${1:-python3}"; OUT="${2:-strict_mode_diagnostics.txt}"; cd "$(dirname "$0")/.."
export EVIDENCE_DIR="$PWD/evidence_input"
{ echo "== environment =="; "$PY" -c "import sys,platform;print(sys.version);print(platform.platform())"; "$PY" -c "import numpy;print('numpy',numpy.__version__)" 2>&1
  "$PY" -c "import scipy;print('scipy',scipy.__version__)" 2>&1 | tail -1; echo "locale: ${LANG:-unset}"
  for MODE in "" "-X dev" "-W error" "-X dev -W error" "-X dev -W error -X faulthandler"; do
    echo; echo "== mode: python ${MODE:-(default)} =="
    "$PY" $MODE -m unittest discover -s code/tests > /tmp/_sd_out.txt 2> /tmp/_sd_err.txt; RC=$?
    echo "process_exit=$RC"; grep -E "^(Ran |OK|FAILED)" /tmp/_sd_err.txt; echo "stderr_lines=$(wc -l < /tmp/_sd_err.txt)"
    grep -v -E "^(Ran |OK|FAILED|\.+$|-+$|$)" /tmp/_sd_err.txt | head -15
  done; } > "$OUT" 2>&1
cat "$OUT"
