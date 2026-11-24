# 01_BASE の由来
`repro_kit/` は第7号ZIP(`g_submission.zip`、SHA-256 `389b5144a81f0c4ea6833856e3d8c74e1da9c2ac039d2372934b04a0af42c6e0`)内の `repro_kit/` を**原本のまま**抽出したもの(変更なし)。キットmanifest(`KIT_MANIFEST_sha256.txt`)SHA-256 `7404d14ca23270b691b61f0586b1480c6808292f93349e358650df47d150b83e`、manifest不一致 0 件。

## 機密情報の混入確認(公開前確認。クロ実施)
- 検索語: private_auth / secret / private_key / BEGIN…KEY / godel_original / AWΦ。結果: 秘密鍵・HMAC秘密情報・`private_auth` ファイルは**検出されず**。
- ヒット: 実行manifest(6件)に、署名方式を説明する文(「HMAC-SHA256 with a secret key held by the research lead … (not stored in the repository)」)があるのみ(鍵そのものではない)。
- **要判断事項(統括)**: `evidence_input/` の認可JSON・実行manifestには、承認者名・承認ID・署名値(HMAC出力。鍵ではない)が含まれる。署名値は鍵ではないが、第三者への開示の可否は統括の判断を要する。非公開とする場合は、原本を変更せず開示用派生物を別途作成する(本構築では作成していない)。
- `01_BASE/repro_kit/` は原本。派生物ではない。
