# Current implementation discovery

Perform this pass against the actual PCE Game Editor checkout before producing commands or assets. Record the checkout commit and discovered limits in the integration manifest.

## Sources of truth

1. Locate `pce-vn-manager.js`, `pce-asset-manager.js`, `template/template_pce_vn_cd`, the project's `project.json`, `assets/pce-vn-scenes.json`, and `assets/pce-assets.json` with `rg --files`.
2. Inspect the exported constants and functions in `pce-vn-manager.js`. In the current implementation the relevant non-writing CD check is `inspectVnSceneDocumentBuild`, but confirm its name and return contract rather than assuming it remains unchanged.
3. Inspect `normalizeCommand`, raw-input validation, scene-pack generation, text encoding, VRAM/font/sprite layout checks, and HuCARD branches. Derive command names, field ranges, scene/command counts, pack-byte limits, supported characters, and per-target behavior from code and preflight output.
4. Inspect `pce-asset-manager.js` exports and the implementations of `importImage`, `inspectPsgJson`, and `importPsgJson`. Confirm image dimensions/options, asset types, animation metadata, PSG version and type checks, and generated-file policy.
5. Read current focused tests, especially `tests/pce-vn-manager.test.js`, CD/HuCARD automatic-runtime tests, and asset-manager tests. Tests are evidence of supported behavior, not a substitute for the implementation.

## Required preflight behavior

- Pass the raw proposed scene document and current asset document to the checkout's non-writing CD inspection before saving generated scenes.
- Fail on any diagnostic with severity `error`; do not rely on normalization to erase bad commands, unresolved scenes/labels, missing assets, unsupported glyphs, or byte overflows.
- Retain returned normalized document, diagnostics, limits, totals, and per-scene byte budgets as evidence.
- Run the actual build after preflight. Generated C/source files and CUE/ROM artifacts, not an in-memory success result, are the delivery gate.

If the current checkout lacks a non-writing inspection API, use its real build preflight on a disposable copy of the official template. Do not patch the engine as part of this skill unless the user separately authorizes engine work.
