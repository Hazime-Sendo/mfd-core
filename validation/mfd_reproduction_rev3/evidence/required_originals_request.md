# 原本の受領状況
2026-11-24 に `MFD_No9_originals.zip`(SHA-256 `cc7d786308e95547fa5683fbd115e9ee80e107030583426b7c77cf941eb568ed`)を受領。ZIPのSHA-256は期待値と一致、内部20ファイルは同梱 `SHA256SUMS.txt` と20/20一致(実測)。

| 項目 | 状態 |
|---|---|
| B-FULL `.m2` 9本 | **受領・収録済み**(03_B_FULL。台帳 full_sha256 と 9/9 一致) |
| B-TIER1 `.npz` 10本 | **受領・収録済み**(04_B_TIER1。台帳 tier1_bytes と 10/10 一致) |
| `MFD_B_REGEN_result.log` | **受領・収録済み**(05_B_REGEN/existing_logs。SHA-256 4f126b8a…ab394 一致) |
| 先行1軌道(ns15_a4)のB-REGEN結果 | **統括の対話記録からの転記を登録済み**(05_B_REGEN/pilot_ns15_a4。原始端末ログ・原対話記録は未受領のため、転記のみ。原記録の提供があれば差異確認) |
| `rbsh6/run_aux_timing/ledger.jsonl` | 未提供。第7号の `ledger_dt0025.jsonl`(SHA-256 5d4016da…b05f)が指示書記載の台帳ハッシュと一致することを実測(指示書は同一確認済みと記載) |
