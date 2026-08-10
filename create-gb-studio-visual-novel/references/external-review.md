# External dialogue review and round trip

## Contents

- Review-pack contract
- Stable IDs
- Export
- Reviewer instructions
- Applying corrections
- Required revalidation

## Review-pack contract

Keep the authoritative scenario JSON unchanged while preparing review material. Export separate concept, character, and full-script Markdown files plus a machine-readable manifest. Include the source scenario SHA-256 in every file so returned corrections cannot silently target a stale draft.

Do not clean up the dialogue during export. A proofreading pack must reproduce current messages and choices exactly, including awkward wording the reviewer needs to see.

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
  --out <review-dir>
```

The exporter fails duplicate scene IDs, unknown jump targets, empty visible text, or duplicate review IDs. Treat its counts and SHA as evidence that the pack matches the source.

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
