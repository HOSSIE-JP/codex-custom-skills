# Usage Examples

## 基本

```text
@ai-character-reference-reconstructor
添付したキャラクター画像から、AI向けのキャラクターリファレンスを再構築してください。
```

## 複数画像の用途を固定

```text
@ai-character-reference-reconstructor
画像1を顔と全体デザインの正本、画像2を背面衣装、画像3を髪飾りの詳細参照として使ってください。
3枚または必要なら4枚の独立画像と、英語タグ辞書、統合タグ列を出力してください。
```

## 第4画像を省略

```text
@ai-character-reference-reconstructor
通常的な人型なので、重要構造が十分に分かる場合は第4画像を作らないでください。
```

## 出力形式をStable Diffusion向けに変更

```text
@ai-character-reference-reconstructor
画像シートの仕様は標準のまま、統合タグ列だけStable Diffusion向けのsnake_caseタグにしてください。
```

## このスキルを使わない例

- 文章だけから新規キャラクターを1枚描く
- 写真の背景を消す
- 既存画像を別画風へ変換する
- 一般的な画像の高解像度化
