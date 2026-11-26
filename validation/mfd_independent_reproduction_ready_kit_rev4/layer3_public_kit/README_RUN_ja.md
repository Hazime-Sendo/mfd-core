# 層III(140ラベル)実行手順(キット Rev.4)
**目的:** 第三者(または別環境)が同一の入力から36テスト(従来19+正準比較17)と全体解析を再実行し、結果を比較できるようにする。本人による別環境実行は「環境間再現」、独立した第三者の実行のみ「第三者再現」と記録する。
## 要件
Python 3.11 以上、NumPy 1.26 以上(`requirements.txt`)。他は標準ライブラリのみ。ネットワーク不要。
## 手順(このフォルダ `repro_kit/` で)
1. 環境確認: `python tools/check_env.py`(`ENV_OK` と表示される)
2. 一括実行: `bash run_all.sh <Python実行ファイル> <名前>` 例: `bash run_all.sh python3 myenv`
   内部で(a)環境確認 (b)入力証拠18ファイルの sha256 照合(`expected_evidence_sha256.txt`) (c)`python -X dev -W error -m unittest discover` で36テスト(従来19+正準比較17) (d)全体解析 `run_analysis.py`(読取専用) (e)出力ハッシュ (f)実行後の入力再照合 を行う。
3. 合格の目安: `Ran 36 tests ... OK`、警告0件、`evidence unchanged`、`INPUT UNCHANGED AFTER RUN`、`run_analysis exit=0`。
4. 実行記録: `python tools/make_execution_record.py "<実行者名>" logs/<名前>`(実行者・日時・環境・出力ハッシュを JSON で保存)
5. 科学的同等性の確認: `python tools/canonical_compare.py labels expected/label_reconstruction_140.json out_<名前>/label_reconstruction_140.json`(および `report expected/analysis_report_expected.json out_<名前>/analysis_report.json`)。比較仕様は `NORMALIZATION_SPEC.md`。原本のバイトSHA照合(原本完全性)とは別の検査であり、正準ハッシュをファイルのハッシュと混同しない。
6. `logs/`、`out_<名前>/` を返送。
## 終了コード(`run_all.sh`)
0=すべて成功 / 1=テスト失敗 / 2=環境NG / 3=入力証拠のハッシュ不一致(実行前に停止) / 4=実行中に証拠が変化 / 5=解析失敗 / 6=実行後に入力が変化。
自己検査: `bash tools/selftest_failure_modes.sh python3`(作業用コピー上で、正常・入力改変・テスト失敗・環境NG の4通りの終了コードを確認。元のキットは変更しない)。結果は `logs/selftest_failure_modes.txt`。
## 参照結果(制作者の再実行)
トップの `reference_run_by_producer/` に保存。140ラベル再構成の原本期待バイトSHAは b0f3536ac809e4668cd3d9e0a50c43285753ee7bc41ac85f640660ffedb10c9e(`expected/label_reconstruction_140.json`)。制作者の再実行であり、独立検証ではない。
## 注意
- `evidence_input/` は公開用の入力(台帳2、軌道容器8、公開用条件ファイル6、公開用由来記録1、SHA256SUMS.txt)です。内部の運用記録は含みません。読取専用で扱い、変更しないでください。
- このキットはシミュレーション、学習、最適化、台帳更新を行いません。
- 固定絶対パスは使いません。入力は `evidence_input/`(環境変数 `EVIDENCE_DIR` で変更可)。
