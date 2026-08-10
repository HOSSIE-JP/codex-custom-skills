# ishi-no-ura-pce-vn-authoring v1.2.0 更新パッケージ

このパッケージは、既存の `ishi-no-ura-pce-vn-authoring` スキルへ上書きする更新差分です。

## v1.2.0の変更点

### 1. 自然な会話を設計段階で作る

各sceneへ「会話設計カード」を追加します。

- 直前の具体的な出来事
- 各人物の開始感情
- 表向きの目的と隠れた動機
- 最初の反応
- 反応→主張→質問／反論→具体例→変化／オチ
- 画面で見せる証拠
- 台詞へ直接書かないテーマの下地
- 終了感情と次sceneへの接続
- 説教、論文調、知識越境、急な改心などの危険

台詞は、PCEの17文字制約へ先に合わせません。自然な口語を作り、音読、話者入れ替え、聞き手の反応を検査した後、意味と息継ぎを壊さずPCE用へ分割します。

### 2. 画像生成を人間へ分離する

スキル自身はChatGPT Image、`image_gen`、その他の画像生成機能を実行しません。

スキルが作るもの:

- asset IDと使用scene
- 画像にする一瞬と物語上の目的
- 人間が添付する参照画像一覧
- 人物配置、画角、視線、表情、ポーズ、小物、背景
- 28:17クロップ用の安全領域
- 別のChatGPT Image会話へそのまま貼れる完成プロンプト
- 禁止事項
- 生成後の受け入れチェック
- 再生成用修正プロンプト雛形

この段階の状態は `PROMPT_READY / IMAGE_PENDING_HUMAN` です。画像生成済みとは報告しません。

人間が行うもの:

1. 参照画像をChatGPT Imageへ添付
2. 完成プロンプトを実行
3. 必要に応じて再生成
4. PCE Game Editorで224×136化・減色・パレット生成
5. background assetとして登録
6. 更新後の `pce-assets.json` をスキルへ戻す

## 適用方法

既存スキルの場所を指定して、同梱の適用スクリプトを実行します。適用前に対象ディレクトリをバックアップしてください。

### Windows PowerShell

```powershell
./apply-update.ps1 -TargetPath "C:\path\to\.agents\skills\ishi-no-ura-pce-vn-authoring"
```

### macOS / Linux

```bash
./apply-update.sh /path/to/.agents/skills/ishi-no-ura-pce-vn-authoring
```

手動で適用する場合は、`SKILL.md`、`VERSION`、`README.md`、`CHANGELOG.md`、`references/`、`scripts/README.md` を既存スキルへ上書きし、`REMOVE_FILES.txt` に記載した旧ファイルを削除します。

## 主な資料

- `SKILL.md`
- `references/natural-dialogue-guidelines.md`
- `references/image-generation-policy.md`
- `references/chatgpt-authoring-workflow.md`
- `references/series-bible.md`
- `references/asset-catalog.md`
- `references/production-checklist.md`

## 画像処理の禁止

スキルは画像の生成、編集、合成、クロップ、リサイズ、減色、パレット化、コンタクトシート作成、画像検査を行いません。Python、Pillow、OpenCV、matplotlib、NumPy、SVG、HTML canvasも画像工程では使いません。

JSON、文字数、分岐到達性、asset IDなど、画像ファイルへ触れないvalidatorは利用できます。
