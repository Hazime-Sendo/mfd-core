# MFD_Independent_Reproduction(第9号案 ④-B 追加証拠パッケージ・構築版)
**状態: 最終整備版 Rev.3(原本20ファイル収録済み。先行1軌道は編成統括の転記として登録)。第三者実行状態: `NOT_EXECUTED_BY_INDEPENDENT_PARTY`。編成統括の検収前は外部送付・公開しない。**

## 構成
01_BASE 第7号repro_kit(原本のまま) / 02_FROZEN_CODE 凍結数理コード4ファイル(原本) / 03_B_FULL 対象9軌道の期待値と案内 / 04_B_TIER1 対象10軌道 / 05_B_REGEN レシピ10件と案内 / 06_VERIFY 独立照合モジュール・一括スクリプト / 07_MANIFEST SHA-256・原典対応表・140分類証拠対応表 / 08_HANDOVER 様式・必要原本リスト・状態。

## 原本の収録状況
B-FULL `.m2` 9本、B-TIER1 `.npz` 10本、B-REGEN実行ログを `MFD_No9_originals.zip`(SHA-256 `cc7d786308e95547fa5683fbd115e9ee80e107030583426b7c77cf941eb568ed`)から**変更なしで**収録。**先行1軌道(ns15_a4)は編成統括の対話記録からの転記として `05_B_REGEN/pilot_ns15_a4/` に登録(原始端末ログではない)。** 詳細は `08_HANDOVER/required_originals_request.md`。

## 機密・開示
この内部版は承認者名・署名値を含む原本を収録しており、**外部送付・公開しない**。第三者向けには承認者名・署名値・承認ID・発行失効時刻を伏せた開示用派生物(別ZIP `MFD_Independent_Reproduction_DISCLOSURE_Rev3.zip`)を使う。

## 含めないもの(指示書第2章)
Gödel++原典、AWΦ中枢技術、private_auth・秘密鍵・HMAC秘密情報、コントローラー全体(必要関数のみ抽出)。

## 区別
原本(01_BASE, 02_FROZEN_CODE)/ 機械抽出(06_VERIFY のモジュール)/ 台帳からの転記による派生物(03〜05 の JSON)/ 新規作成(その他)。`07_MANIFEST/origin_correspondence.csv` に全ファイルの区別を記載。

## 状態の維持
G2正式判定: 69 MATCH / 71 PARTIAL / 0 MISMATCH(変更なし)。G4: HOLD(変更なし)。「技術的分類照合 140/140」は既存記録(指示書第3章)の引用であり、本パッケージの実行結果ではない。
