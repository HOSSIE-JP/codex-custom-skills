# Shared pack to PCE mapping

The canonical source is the complete six-file `source/vn-authoring/` pack owned by `write-visual-novel-scenario`. Its `script.json` is format version 2 with a positive integer revision, approval status, stable lowercase ASCII IDs, typed `stateVariables`, semantic `cues`, `endings`, and `scenes`. PCE data is derived and must retain the six-file aggregate SHA.

## Entry mapping

`emit_pce_scenes.py` supports this strict subset after the shared full-pack validator passes:

- `line` -> one PCE `message`; the character bible's display name is used and voice remains empty.
- A terminal unconditional `choice` -> one PCE `choice`. Option `text` becomes `label`. `setState` must assign one common integer state variable on every option. `when`, boolean/string choice state, and multi-variable assignments require manual mapping and are rejected.
- A terminal `jump` -> one PCE `jump`.
- Integer `state` operations `set`, `add`, and `subtract` -> PCE `variable`. `toggle`, conditions, and non-integer state require manual mapping and are rejected.
- `cue` -> the exact command list or explicit omission in the PCE cue-map sidecar.

The helper deliberately imposes no remembered speaker/text length caps. The current checkout's raw-input inspection, text encoder, glyph budget, and scene-pack preflight are authoritative.

## `when` and state-write rejection are absolute, not partial

`emit_pce_scenes.py`'s `emit()` raises the moment it sees a `when` key on any entry or any choice option — the entire emission aborts, not just the offending entry. State writes are equally strict: a choice's `setState` must assign exactly one variable common to every option, and `scalar_int()` explicitly checks `isinstance(value, bool)` and rejects a `bool` even though Python's `bool` is technically an `int` subclass — a choice option that writes `true`/`false` fails even though it "looks like" a 0/1 integer.

**Workaround for reaction-only branching.** When a design only wants a scene to briefly acknowledge which prior choice was made — one or two lines of differing reaction text that do not otherwise affect later branching — do not reach for `when` + state. Restructure as a **structural scene split**: give the choice's two options two tiny sibling scenes (e.g. `scene_x_a`, `scene_x_b`), each holding only the reaction line, and have both `nextSceneId` into a shared continuation scene (`scene_x_core`). This stays inside the emitter's supported subset, and often removes the need for the state variable entirely — delete it and set `project-brief.json`'s `branching.stateVariables` back to `[]` if nothing else reads it.

## Cue map is flat, not branch-aware

`emit_pce_scenes.py` resolves every `cue` entry with a single global lookup, `cue_map.get(cue_id)` — one cue ID always maps to exactly one command list, with no notion of which scene or branch is asking. If the shared pack reuses one semantic cue ID across scenes that want different PCE treatment (for example, one `cue.ending_resolution` cue referenced from three different endings, each wanting a different background/music), all three uses get the byte-for-byte identical commands.

This cannot be fixed in the cue map or at the PCE integration layer at all — it has to be decided when the cue is first authored (or refactored) in the shared pack itself: split it into distinct per-branch IDs (e.g. `cue.ending_resolution_true` / `cue.ending_resolution_normal` / `cue.ending_resolution_bad`), each with its own tailored `emotion`/`visibleContent`, and give each its own cue-map entry. Before running the emitter, check whether any cue ID is referenced from more than one scene with a different intended PCE outcome.

## Cue separation

Canonical cues contain `id`, `kind`, `emotion`, `narrativePurpose`, `characters`, `visibleContent`, `musicFunction`, and `playbackIntent`. They contain no PCE asset IDs, dimensions, formats, filenames, engine names, or commands.

The target cue map is separate:

```json
{
  "formatVersion": 1,
  "cues": [
    { "cueId": "cue.rooftop.reveal", "commands": [
      { "type": "background", "assetId": "rooftop_bg", "transition": "fade", "x": 2, "y": 1 }
    ] }
  ]
}
```

Allowed helper-emitted cue command types are `background`, `sprite`, `spritemove`, PSG-only `audio`, `effect`, `wait`, `spritetext`, and non-ADPCM `cache`. The engine preflight remains final.

## Approval, stable IDs, and accounting

- Run `validate_shared_pack.py` on the project/authoring directory. It imports the shared `validate_pack(..., require_approved=True)`, requires all four self-review passes, requires a resolved external-review consultation state, and computes the six-file aggregate SHA.
- Pass that report to the emitter and manifest builder. Any aggregate mismatch is stale and fails.
- The source map records deterministic shared scene/state ID to PCE ID mappings. Every entry and choice option is mapped exactly once. Cue definitions and endings are added by the integration manifest builder.
- The final manifest is itself checked by the shared `validate_integration_manifest.validate_manifest`, proving every non-scene shared ID is consumed or explicitly substituted once.

## Migrating PCE v2 scenes

`migrate_pce_v2.py` emits a canonical format-version-2, revision-1, `REVIEW_REQUIRED` script skeleton. It preserves valid IDs and assigns content-derived IDs to invalid scene, state, speaker, line, option, cue, and ending identities. Direct terminal choices/jumps and simple state operations are converted; presentation/audio/control commands become semantic placeholder cues. Exact raw PCE commands live only in the target cue map and ambiguity report. Merge suggested characters into the full pack, resolve every ambiguity, rerun shared validation, and obtain approval before integration.
