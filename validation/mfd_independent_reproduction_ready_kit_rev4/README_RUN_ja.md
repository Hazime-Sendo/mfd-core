# MFD 独立再現準備キット Rev.4(Linux / WSL2 / Google Colab)
**目的**: 保存済みデータからの**再集計・再分類のみ**を、層I・II・IIIに分けて一括再実行できるようにする。**新規の軌跡・試行・シミュレーションは行わない。モデル変更なし。**
**位置づけ**: `reference_run_by_producer/` は**制作者(Claude)による再実行**であり、**第三者独立実行ではない**。第三者独立実行は未実施(G2 69 MATCH/71 PARTIAL/0 MISMATCH、G4 HOLD は不変)。

## 要件と実行
Python 3.11以上、NumPy 1.26以上(制作者の確認環境: Python 3.13.18 / NumPy 2.5.3(厳格診断では NumPy 2.3.5 も確認)、`requirements-pinned.txt`)。ネットワーク不要。
```
unzip MFD_Independent_Reproduction_Ready_Kit_Rev4.zip && cd MFD_Independent_Reproduction_Ready_Kit_Rev4
bash run_all_rev8.sh python3 myrun
```
入力は読取専用(実行前後にSHA-256照合。層IIIは作業コピー上で実行)。出力は `runs/myrun/` のみ。同名run_nameは拒否。ログ(`logs/console.txt`、`logs/pip_freeze_filtered.txt`)を保存。実行の最初に `tools/verify_kit_manifest.py`(状態ベースのマニフェスト検査。下記)を実行し、失敗時は先へ進まない。

## マニフェスト検査の状態(Rev.4、`tools/verify_kit_manifest.py`)
各ファイルは次のいずれか1つの状態で報告される: `OK`(通常ファイルを読み取り、SHA-256一致)/`MISMATCH`/`NOT_FOUND`(存在しない)/`UNREADABLE`(存在するが読み取り不能)/`SPECIAL_STATE`(シンボリックリンク、Windowsの再解析ポイント・クラウドプレースホルダー等。**読み取れても合格にしない**)/`PATH_RESOLUTION`(パスを解決できない。長いパス等)。ほかに、未登録ファイル、公開許可リスト(`tools/public_allowlist.txt`)にないファイル、分類不能な種別、重複・不正パス、ZIP CRCを数える。終了コード: 0=全件OK / 1=完全性の問題 / 2=環境・ファイル状態のため**検証できなかった**(合格ではない)。**OneDrive等の同期フォルダではなく、通常のローカルディスクに新規展開して実行すること**(同期フォルダ上では `SPECIAL_STATE` / `PATH_RESOLUTION` になり得る)。検証器自体の回帰テストは `tools/test_verify_kit_manifest.py`(合成ミニキット上のみ。実キットは変更しない)。

## 層ごとの入力・コード・期待結果・判定条件・限界
| 層 | 入力 | コード | 期待結果(合格の目安) | 限界 |
|---|---|---|---|---|
| I(300試行) | `layer1_300trial/data/dmax_sweep_runs.jsonl`(SHA 8c3c53b0…d8d70) | `rev3_clip_and_bootstrap.py` | クリップ比セル平均 30セル 0.9891–1.0039(±6e-5)、非推定0、τ(a) bootstrap SD: 5.17/1.65/0.29/0.06/0.07、slope−U0 CI a=8 [4,140], a=16 [−94,−10] | 保存記録の再集計。bootstrapのビット一致は確認環境のみ主張 |
| II(33軌跡) | `layer2_33traj/`: 台帳2、B-FULL `.m2` 9、B-TIER1 `.npz` 10、凍結コード4(ハッシュ検査)、ns15の4軌跡(layer3 evidence_input) | `mfd_independent_verify.py`(原典から機械抽出)、`extra_ns15_check.py`(Rev.2追加) | B-FULL 9/9(ファイルSHA・サイズ・12配列・内容ハッシュ・指標・分類4/4)、B-TIER1 10/10(`x_final`から真の終端構造量を凍結kabschで再構成、分類4/4)、ns15 4軌跡×(full,tier1) 8/8。比較108分類 | **33軌跡中21軌跡のみ軌跡データあり**(9+10+2)。**残り12軌跡は台帳要約のみ**で、native/mirrorの再分類は不可(分岐非依存の stagnation/unconverged/anomaly のみ)。19軌道分の存在確認を33軌道全体の再現成立とみなさない |
| III(140ラベル) | `layer3_public_kit/`(18入力、公開代替の `public_conditions_manifest_01–06.json` と `T3-DT01_public_provenance.json`) | 36テスト(従来19+正準比較17)、`run_analysis.py`、`tools/canonical_compare.py` | `Ran 36 tests OK`、`evidence unchanged`、**[3a] 原本完全性**: 出力ラベルのバイトSHA b0f3536a…10c9e(参考表示)、**[3b] 科学的同等性**: 構造化・正準化比較で 140レコード一致(ラベルは完全一致、報告は相対1e-9)、MATCH 69/PARTIAL 71/MISMATCH 0 | 140=分類照合数であり実験数ではない。台帳要約由来のラベルは独立確認ではない |

終了コード: 0=成功 / 1=比較またはテスト失敗 / 3=マニフェスト・入力の完全性不一致 / 5=解析失敗 / 7=Layer III正準比較不一致 / 10=run_name重複。
**テスト本体の成功**と**プロセス全体の終了コード**は `layer3_workcopy/logs/*_exit.txt` に別々に記録される(`unittest_result` と `process_exit`)。`tools/strict_mode_diagnostic.py`(最大5回のサブプロセス。テスト本体・NumPy読込・インタープリタ単体を分離)と `layer3_public_kit/tools/strict_mode_diagnostics.sh` で、厳格モードの結果とプロセス終了コードを別々に取得できる。環境変数 `STRICT_DIAG=1` で一括実行の末尾に追加実行できる。

## 出力されるもの
`runs/<name>/layer1_out/`、`layer2_out/`(`verify_raw.json`、`ns15_check.json`、**`MFD_LayerII_33_Trajectory_Asset_Matrix.csv`**)、`layer3_workcopy/out_<name>/`、`logs/`。

## B-REGEN
`layer2_33traj/05_B_REGEN/` にはレシピ10件と、既存の端末記録の**伏せ字版**(利用者名・ホスト名を除去、制御文字除去。原本ではなく派生物。SHAは別)のみを収録。**再生成(新規数値計算)は禁止のため本キットでは実行しない**。9軌道は原端末ログで9/9 PASS、先行1軌道(ns15_a4)は編成統括の転記で原始端末ログではない。

## 公開代替物について
層IIIの入力から、内部の運用制御・権限関連情報を含む6ファイルと由来記録1ファイルを除外し、科学的検証条件のみを抽出した公開用派生物 `public_conditions_manifest_01–06.json`(第3版)と `T3-DT01_public_provenance.json` に置換した。派生物であり新しいSHA-256を持つ。本キット内のどのマニフェストにも、除外した資産の名称・パス・ハッシュは含まれない。原本との対応は非公開管理資料にのみ記録。
## 限界
1. 層II: 12軌跡は軌跡データなし(PARTIAL)。12件について独立した完全再分類ができたとは主張しない。2. 第三者実行 未実施(制作者の再実行は独立検証ではない)。3. Linux/WSL2のみ検証。4. 本キットの再実行は再集計・再分類で、シミュレーション再実行ではない。5. Work環境(Windows、Python 3.12.14、NumPy 2.3.5)で観測された厳格デバッグモードのインタープリタ終了時異常は、制作側環境では再現せず、原因は未特定。

6. Google Colab用の独立検証Notebook(`MFD_Rev8_Independent_Verification.ipynb`)は別納品。Notebookの制作と実際の独立実行は別であり、制作側で実行できた場合も独立検証結果として扱わない。
