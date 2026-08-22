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
