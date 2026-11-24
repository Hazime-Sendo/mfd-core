# 06_VERIFY(独立照合モジュール)
- `mfd_independent_verify.py`: コントローラー(SHA-256 `12bccc7f870412b46f97b33b9c2f26da34a9ab36a9cc367ba8a094ab3152ba5d`)から13項目(ARRAY_ORDER, MAGIC, M2Error, sha_bytes, sha_file, arrays_hash, _unshuffle, m2_unpack, read_bytes, m2_read, tier1_arrays, evaluate, _jd)を**行単位で機械抽出**。`extraction_lineage.json` に原典の行番号・抽出前後のテキストSHA-256を記録(変更箇所なし)。
- 追加(原典に無い部分): importlib ローダ、凍結コード4ファイルのSHA-256検査(不一致なら停止)、`MFDTrialSpec` の最小再掲、検証ロジック。**godel_original・提案写像機構への依存は無い。**(抽出元の `import godel_original` 行は抽出対象外)
- 終端構造量: `classes_of()` は `x_final` から凍結 `kabsch_rmsd` で**真の計算終端**のRMSDを算出する(最終保存フレームは使わない)。第7号の `labels.py` は変更していない。
- 判定は行わず生結果JSONを出力する(合格基準は指示書第9章。許容誤差による事後合格は禁止)。
