#!/usr/bin/env bash
# キットの失敗時終了コードの自己検査(作業用コピー上で実行。元のキットは変更しない)。 bash tools/selftest_failure_modes.sh <python>
set -u; PY="${1:-python3}"; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; T="$(mktemp -d)"; ok=0
run(){ rm -rf "$T/k"; cp -r "$ROOT" "$T/k"; rm -rf "$T/k/logs"/* "$T/k"/out_*; ( cd "$T/k" && eval "$1" && bash run_all.sh "$PY" st >/dev/null 2>&1 ); echo $?; }
a=$(run ":"); echo "正常: exit=$a (期待 0)"; [ "$a" = 0 ] && ok=$((ok+1))
b=$(run "echo tamper >> evidence_input/ledger_dt0025.jsonl"); echo "入力改変: exit=$b (期待 3)"; [ "$b" = 3 ] && ok=$((ok+1))
c=$(run "sed -i 's/\"stagnation\")/\"native\")/' code/tests/test_analysis.py"); echo "テスト失敗: exit=$c (期待 1)"; [ "$c" = 1 ] && ok=$((ok+1))
d=$(run "sed -i 's/numpy>=1.26/numpy>=1.26/' requirements.txt; printf 'import sys\nsys.exit(1)\n' > tools/check_env.py"); echo "環境NG: exit=$d (期待 2)"; [ "$d" = 2 ] && ok=$((ok+1))
echo "期待どおり: $ok/4"; rm -rf "$T"; [ $ok -eq 4 ]
