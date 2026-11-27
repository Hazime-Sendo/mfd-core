# 04_B_TIER1(対象10軌道)
**原本の `.npz` 10本を収録(変更なし)。** 入手: `MFD_No9_originals.zip`(SHA-256 `cc7d786308e95547fa5683fbd115e9ee80e107030583426b7c77cf941eb568ed`)内 `B_TIER1/`。SHA-256は原本一覧と一致(実測)。台帳 `tier1_bytes` とのサイズ一致 10/10(実測)。

ファイル: `ns10_a4_D500_dt0.0025_s0.npz`, `ns12_a0_D500_dt0.0025_s0.npz`, `ns12_a4_D500_dt0.0025_s0.npz`, `ns12_a8_D500_dt0.0025_s0.npz`, `ns15_a4_D500_dt0.0025_s0.npz`, `ns16_a8_D500_dt0.0025_s0.npz`, `ns18_a8_D500_dt0.0025_s0.npz`, `ns2_a4_D500_dt0.0025_s0.npz`, `ns4_a4_D500_dt0.0025_s0.npz`, `ns9_a8_D500_dt0.0025_s0.npz`

注意: tier-1 単独では元の全12配列の内容ハッシュ(arrays_sha256)は再構成できない。ns15_a4・ns16_a8 は最終保存フレームと計算終端が1・6ステップ異なるため、`x_final` から凍結関数で真の計算終端のRMSDを算出する(第7号の labels.py は変更しない)。

クロの構築時照合(第三者検証ではない): `x_final` からの終端構造量の再構成と分類(4×10=40)が10/10で一致(`06_VERIFY/claude_construction_verification/`)。
