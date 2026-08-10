# BLOCKED: HUMAN_APPROVAL_REQUIRED

- 対象設計: `scenario-design.md`
- 検出revision: N
- 不足情報:
  - `approval_status` が `APPROVED` ではない
  - または対象revisionの明示承認が現在の依頼にない

有効な承認文:

```text
添付した scenario-design.md revision N を承認します。
このrevisionを正本として第2段階へ進めてください。
```

承認されるまで、台詞、画像、JSONは生成しません。
