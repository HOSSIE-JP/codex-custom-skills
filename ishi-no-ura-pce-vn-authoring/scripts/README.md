# scriptsの扱い

v1.2.0では、スキル内で画像生成や画像編集を行いません。
スキルが作るのは、人間が別途ChatGPT Imageへ渡すイベントスチル用プロンプトパックです。

## 使用禁止・削除対象

- `prepare_event_stills.py`
- Pillowを導入するための`requirements.txt`
- 画像生成ツールを自動実行するスクリプト
- 画像のクロップ、リサイズ、減色、合成、画像検査を行うスクリプト

## 継続利用できるスクリプト

次の条件をすべて満たすJSON／テキスト専用スクリプトだけ継続利用できます。

- PNG、JPEG、WebPその他の画像ファイルを開かない
- 画像を生成、変更、変換、検査しない
- JSON、テキスト、CSV、manifestだけを扱う

例:

- `validate_pce_vn.py`
- `integrate_event_stills.py`のうちJSON commandだけを編集する処理
- `package_episode.py`のうち既存ファイルを梱包するだけの処理

既存スクリプトが画像ファイルの内容を読み込む実装へ変更された場合は、この例外から外れます。
