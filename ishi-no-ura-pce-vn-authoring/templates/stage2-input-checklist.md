# 第2段階 入力チェックリスト

## 承認

- [ ] `scenario-design.md` がある
- [ ] `workflow: ishi-no-ura-pce-vn`
- [ ] `document_type: scenario-design`
- [ ] `schema_version: 1`
- [ ] `approval_status: APPROVED` または現在の依頼に明示承認がある
- [ ] `approved_revision == revision`
- [ ] 承認後に設計本文が変更されていない

## 正本

- [ ] `series-bible.md`
- [ ] `asset-catalog.md`
- [ ] 複製先 `assets/pce-vn-scenes.json`
- [ ] 複製先 `assets/pce-assets.json`

## イベントスチル

- [ ] 承認済みスチル計画がある
- [ ] キャラクター参照spriteがある
- [ ] 話数別asset IDが固定されている
- [ ] 完成JSON生成時点で全IDが `pce-assets.json` に登録済み

## 完成条件

- [ ] JSON parse成功
- [ ] `version: 2`
- [ ] `startScene: logo`
- [ ] `logo`／`title`／`eye_catch` 維持
- [ ] title開始jump更新
- [ ] 新話末尾から `eye_catch`
- [ ] 2択×2回
- [ ] 全分岐から必須スチル、エンディング、`eye_catch` 到達
- [ ] 約220〜280message
- [ ] 各行17文字以内
- [ ] 各scene 4096 bytes以内
- [ ] `voiceAssetId` は空文字
- [ ] 登録済みasset IDだけを参照
- [ ] CD-ROM2／HuCARDの両方で進行可能
