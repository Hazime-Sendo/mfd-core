# A2-v2 第三者再現キット 実行手順(第5号 E2)
**目的:** 第三者(または別環境)が同一の入力から19テストと全体解析を再実行し、結果を比較できるようにする。本人による別環境実行は「環境間再現」、独立した第三者の実行のみ「第三者再現」と記録する。
## 要件
Python 3.11 以上、NumPy 1.26 以上(`requirements.txt`)。他は標準ライブラリのみ。ネットワーク不要。
## 手順(このフォルダ `repro_kit/` で)
1. 環境確認: `python tools/check_env.py`(`ENV_OK` と表示される)
2. 一括実行: `bash run_all.sh <Python実行ファイル> <名前>` 例: `bash run_all.sh python3 myenv`
   内部で(a)環境確認 (b)入力証拠23ファイルの sha256 照合(`expected_evidence_sha256.txt`) (c)`python -X dev -W error -m unittest discover` で19テスト (d)全体解析 `run_analysis.py`(読取専用) (e)出力ハッシュ (f)実行後の入力再照合 を行う。
3. 合格の目安: `Ran 19 tests ... OK`、警告0件、`evidence unchanged`、`INPUT UNCHANGED AFTER RUN`、`run_analysis exit=0`。
4. 実行記録: `python tools/make_execution_record.py "<実行者名>" logs/<名前>`(実行者・日時・環境・出力ハッシュを JSON で保存)
5. 参照結果との比較: `python tools/compare_runs.py out_<名前> out_sys313_np253`(ラベル140件はバイト一致、浮動小数は相対 1e-9 まで許容)
6. `logs/`、`out_<名前>/` を返送。
## 終了コード(`run_all.sh`)
0=すべて成功 / 1=テスト失敗 / 2=環境NG / 3=入力証拠のハッシュ不一致(実行前に停止) / 4=実行中に証拠が変化 / 5=解析失敗 / 6=実行後に入力が変化。
自己検査: `bash tools/selftest_failure_modes.sh python3`(作業用コピー上で、正常・入力改変・テスト失敗・環境NG の4通りの終了コードを確認。元のキットは変更しない)。結果は `logs/selftest_failure_modes.txt`。
## 参照結果(作成者の4環境。同一マシン・同一OS)
`logs/` と `out_*` に保存済み(Py3.13.18/NP2.5.3、3.14.6/2.3.5、3.12.3/2.0.2、3.11.18/1.26.4)。140ラベル再構成(`label_reconstruction_140.json`)の sha256 は b0f3536ac809e4668cd3d9e0a50c43285753ee7bc41ac85f640660ffedb10c9e(4環境で同一)。
## 注意
- `evidence_input/` は凍結証拠 ZIP(sha256 b7c06db713691f4627f7b5e34630d90b44f24e6e732ebb880ae132c81bbb366f)の展開コピーです。読取専用で扱い、変更しないでください。
- このキットはシミュレーション、学習、最適化、台帳更新を行いません。
- 固定絶対パスは使いません。入力は `evidence_input/`(環境変数 `EVIDENCE_DIR` で変更可)。
