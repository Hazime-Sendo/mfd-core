#!/usr/bin/env bash
# 使い方: bash run_repro.sh [python実行ファイル] [ログ名]   終了コード: 0=19テスト成功かつ証拠不変、1=テスト失敗、4=証拠が変化
set -u
PY="${1:-python3}"; TAG="${2:-run}"
cd "$(dirname "$0")"; mkdir -p logs
hash_tree(){ (cd evidence_input && sha256sum * | sort -k2); }
hash_tree > "logs/${TAG}_evidence_before.txt"
{ echo "== env =="; uname -a; "$PY" -c "import sys,platform,numpy;print(sys.version);print('numpy',numpy.__version__);print(platform.platform())"
  echo "== cmd: $PY -X dev -W error -m unittest discover -s code/tests -v =="; } > "logs/${TAG}_env.txt" 2>&1
EVIDENCE_DIR="$PWD/evidence_input" "$PY" -X dev -W error -m unittest discover -s code/tests -v > "logs/${TAG}_stdout.txt" 2> "logs/${TAG}_stderr.txt"
RC=$?
echo "exit=$RC" > "logs/${TAG}_exit.txt"
hash_tree > "logs/${TAG}_evidence_after.txt"
if cmp -s "logs/${TAG}_evidence_before.txt" "logs/${TAG}_evidence_after.txt"; then echo "evidence unchanged" >> "logs/${TAG}_exit.txt"; CH=0; else echo "EVIDENCE CHANGED" >> "logs/${TAG}_exit.txt"; CH=4; fi
tail -4 "logs/${TAG}_stderr.txt"; cat "logs/${TAG}_exit.txt"
[ $CH -ne 0 ] && exit 4
[ $RC -ne 0 ] && exit 1
exit 0
