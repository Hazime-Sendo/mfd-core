#!/usr/bin/env bash
# 使い方: bash run_all.sh <python実行ファイル> <名前>
# 終了コード: 0=すべて成功 / 1=テスト失敗 / 2=環境NG / 3=入力証拠のハッシュ不一致(実行前) / 4=実行中に証拠が変化 / 5=解析失敗 / 6=実行後に入力が変化
set -u; PY="${1:-python3}"; TAG="${2:-run}"; cd "$(dirname "$0")"
"$PY" tools/check_env.py || { echo "ENV NG"; exit 2; }
"$PY" tools/verify_inputs.py || { echo "INPUT HASH MISMATCH"; exit 3; }
bash run_repro.sh "$PY" "$TAG"; RC=$?
if [ $RC -eq 4 ]; then echo "EVIDENCE CHANGED DURING TESTS"; exit 4; fi
mkdir -p "out_$TAG"
(cd code && "$PY" -X dev -W error run_analysis.py ../evidence_input "../out_$TAG" > "../logs/${TAG}_run_analysis.txt" 2>&1); RA=$?
echo "run_analysis exit=$RA" | tee -a "logs/${TAG}_exit.txt"
(cd "out_$TAG" && sha256sum * ) > "logs/${TAG}_outputs_sha256.txt" 2>/dev/null
"$PY" tools/verify_inputs.py > "logs/${TAG}_inputs_after.txt" 2>&1; VA=$?
cat "logs/${TAG}_inputs_after.txt"; [ $VA -eq 0 ] && echo "INPUT UNCHANGED AFTER RUN"
[ $VA -ne 0 ] && exit 6
[ $RA -ne 0 ] && exit 5
[ $RC -ne 0 ] && exit 1
exit 0
