# Changelog

## 1.2.0 - 2026-07-27

### Changed

- シナリオ設計へscene単位の「会話設計カード」を追加
- 直前の出来事、開始感情、人物の目的、反応の連鎖、終了感情を設計段階で固定
- 教訓を長い説教で説明せず、具体的な出来事と当事者の実感から伝える規則へ変更
- 台詞執筆を「自然な口語の作成」と「PCE表示用分割」の二段階へ変更
- 音読テスト、話者入れ替えテスト、聞き手テストを追加
- スキル自身によるイベントスチル画像生成を廃止
- 画像工程を、人間がChatGPT Imageへ投入する完成プロンプト引き渡し方式へ変更
- 画像生成待ち、PCE登録済み、JSON組み込み済みを状態で区別

### Added

- `references/natural-dialogue-guidelines.md`
- 画像プロンプト引き渡し票
- 再生成用修正プロンプト雛形
- `PROMPT_READY / IMAGE_PENDING_HUMAN / IMAGE_PROVIDED / PCE_REGISTERED / SCRIPT_INTEGRATED` の状態管理

### Prohibited

- スキルからChatGPT Image、`image_gen`、その他の画像生成機能を実行すること
- プロンプトを作っただけで画像生成済みと報告すること
- 画像生成前の未登録assetをstrictな完成JSONへ書くこと
- Pythonその他のプログラムによる画像生成、編集、変換、画像検査

### Retained

- PCE Game Editorでの224×136化、減色、パレット生成、background asset登録
- JSON、文字数、分岐到達性、asset IDなど画像へ触れないvalidatorの利用

## 1.1.0 - 2026-07-27

- イベントスチルの生成手段をChatGPT Imageへ固定
- 画像工程でのPython利用を禁止
- 224×136化とPCE向け変換をPCE Game Editorへ移管
