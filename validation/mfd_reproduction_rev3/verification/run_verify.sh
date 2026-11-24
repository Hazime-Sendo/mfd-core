#!/usr/bin/env bash
# 第三者実行用の一括スクリプト。原本(ledger / full / tier1)を読み取り専用として扱い、出力は別ディレクトリへ書く。
# 使い方: bash run_verify.sh <ledger.jsonl> <full_dir> <tier1_dir> <out_dir> [--regen]
set -u
LEDGER="$1"; FULL="$2"; TIER1="$3"; OUT="$4"; REGEN="${5:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"; PKG="$(cd "$HERE/.." && pwd)"; mkdir -p "$OUT"
echo "実行者・検証者・日時・環境は 08_HANDOVER の様式に記録すること" | tee "$OUT/00_note.txt"
sha256sum "$LEDGER" | tee "$OUT/ledger_sha256.txt"            # 期待: 5d4016da490f699ab190b2c5add3ca185b8ca3b1ff6a2a85af9ab307bf76b05f
( cd "$PKG" && sha256sum -c 07_MANIFEST/sha256_manifest.txt ) > "$OUT/package_integrity.log" 2>&1; echo "package_integrity exit=$?"
( cd "$PKG/01_BASE/repro_kit" && bash run_all.sh ) > "$OUT/kit_run_all.log" 2>&1; echo "kit run_all exit=$?" | tee "$OUT/kit_run_all.exit"   # 第7号既存テスト(目標 19/19)
python3 -I "$HERE/mfd_independent_verify.py" --ledger "$LEDGER" --full-dir "$FULL" --tier1-dir "$TIER1" $REGEN --out "$OUT/verify_raw.json" 2>&1 | tee "$OUT/verify.log"
echo "verify exit=${PIPESTATUS[0]}"
