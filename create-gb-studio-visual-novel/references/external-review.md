# External dialogue review and round trip

## Contents

- Review-pack contract
- Self-review prerequisite
- Stable IDs
- Export
- User consultation gate
- Reviewer instructions
- Applying corrections
- Required revalidation

## Review-pack contract

Treat the review pack as a required creation artifact, not an optional response to a later proofreading request. Generate it after the first complete scenario draft and before image production or generated GB Studio resources. Regenerate it whenever the project brief, character bible, or scenario changes.

Always write these three Markdown files to `source/external-review`:

1. `01_concept.md`
2. `02_character_settings.md`
3. `03_scenario_script.md`

Also write `review-manifest.json` as supporting evidence. The manifest never replaces one of the three required Markdown files. Fail the creation gate when any required file is missing, when counts disagree with the scenario, or when the recorded source SHA-256 is stale.

Keep the authoritative scenario JSON unchanged while preparing review material. Include the source scenario SHA-256 in every file so returned corrections cannot silently target a stale draft.

Do not clean up the dialogue during export. A proofreading pack must reproduce current messages and choices exactly, including awkward wording the reviewer needs to see.

## Self-review prerequisite

Before export, the authoring agent must run mechanical/lint, read-aloud, character-voice, and exposition/branch-join passes against the complete scenario. Apply accepted corrections to the authoritative JSON, rerun lint, and record specific notes in `selfReviews`. Mark `externalReviewPack.selfReview.status` as `complete` only after every pass is complete. The exporter must reject a new-format brief unless the aggregate status is `complete` and every configured `selfReviews` pass is `pass` with a non-empty evidence note.

Self-review improves the draft that is handed off; it does not count as independent external review. Keep `manualReviews` required until a separate reviewer returns results.

## Stable IDs

Give each message an ID derived from the stable scene ID and message order, such as `c12-M03`. Give choices and options their authored IDs, such as `choice_2-O1`. IDs are addresses, not display text; do not renumber scenes to make prose prettier.

When a scene contains variants, include the variant key in the ID. Preserve jumps, waits, route-ending commands, state changes, and return/reset commands as structural annotations even though they are not prose.

## Export

Run:

```powershell
python scripts/export_vn_review_pack.py \
  --brief <project-brief.json> \
  --bible <character-bible.json> \
  --scenario <scenario.json> \
  --rules <language-rules.json> \
  --out <project>\source\external-review
```

The exporter fails duplicate scene IDs, unknown jump targets, empty visible text, or duplicate review IDs. Treat its counts and SHA as evidence that the pack matches the source. Do not advance to image production or GB Studio resource generation until this command succeeds and all three Markdown files exist.

## User consultation gate

Immediately after export, present the user with:

1. the autonomous self-review summary and material changes;
2. unresolved wording or structural concerns;
3. clickable paths to all three Markdown files;
4. the manifest scenario SHA-256 and counts.

Then ask: `外部校正結果を待ってから画像・実装へ進みますか。それとも現版で暫定的に進め、返却後に再生成しますか？`

Record the answer in `externalReviewPack.userConsultation.status` as `awaiting-external-review`, `proceeding-provisionally`, `waived-by-user`, or `complete`. Leave it `pending-user-decision` before the answer. Regenerate the pack after changing the project brief so the manifest records the current workflow state.

If the answer is `awaiting-external-review`, pause image and generated-resource production. If it is `proceeding-provisionally`, record that fonts, scenes, ROM, Web output, and affected images or layouts must be regenerated after accepted corrections. Never upload or transmit the pack to an external AI or service unless the user explicitly authorizes that action; preparing and linking local files is not authorization to send them.

## Reviewer instructions

Ask the reviewer to return prose changes as:

```text
reference ID | before | after | reason
```

Ask for structural changes in a separate section. State the message-window line budget, point of view, speaker constraints, content boundaries, character voice rules, and which facts/branch outcomes must remain unchanged.

Review concept and character settings before the full script. Request separate passes for read-aloud flow, character voice, exposition, and branch joins. Do not ask one unconstrained prompt to rewrite the entire scenario while also preserving exact branch semantics.

## Applying corrections

Verify the review manifest SHA against the current scenario before editing. Apply changes by reference ID to the authoritative JSON, reject stale IDs and mismatched `before` text, and record accepted/rejected reasons. Do not patch generated `.gbsres` dialogue directly.

When a sentence must split, create explicit new message IDs in the source and rebuild the review pack. Do not hide two messages inside one string with incidental newlines if runtime behavior depends on message boundaries.

## Required revalidation

After applying corrections:

1. rerun Japanese lint and the four independent review passes;
2. rebuild font pages and validate every compiled byte sequence;
3. regenerate scenes and verify every branch join and ending history;
4. rebuild ROM and Web exports;
5. replay changed routes with real input and confirm text-window fit;
6. record the new scenario SHA and ROM SHA.
