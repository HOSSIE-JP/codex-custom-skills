# ishi-no-ura-pce-vn-scenario-design

「いしのうらにいる！？」の第1段階専用スキルです。

## 役割

企画からシナリオ設計を作りますが、台詞全文、画像、完成JSONは作りません。出力は人間が修正・承認するための `scenario-design.md` です。

## 重要な動作

- 出力は必ず `REVIEW_REQUIRED`
- 同じ依頼内で第2段階へ進まない
- revisionごとに承認を分ける
- イベントスチルは場面・構図・プロンプトまで設計し、画像生成はしない
- 実装上のJSON commandは作らない

## 主な入力

- 話数、仮題、題材、風刺したい行動
- 大枠の出来事、因果応報、オチ
- `series-bible.md`
- `asset-catalog.md`
- 必要に応じて既存話JSONとアセット台帳

## 主な出力

- `scenario-design.md`
- 必要に応じて人間向けの比較案

`templates/scenario-design-template.md` を出力の基準にします。
