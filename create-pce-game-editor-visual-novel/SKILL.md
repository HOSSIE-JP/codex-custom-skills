---
name: create-pce-game-editor-visual-novel
description: Build, port, integrate, and validate Japanese visual novels for PCE Game Editor from an approved shared VN authoring pack. Use for PCE CD-ROM2 VN scene emission, image and sprite integration, PSG cue mapping, v2 scene migration, CUE builds, optional HuCARD builds, or Geargrafx playthrough QA. Do not use for scenario writing before an approved shared pack exists.
---

# Create PCE Game Editor Visual Novel

Turn an approved `source/vn-authoring/script.json` into a traced PCE Game Editor VN. The shared pack owns dialogue, choices, state meaning, endings, and semantic cues; this skill owns PCE assets, commands, builds, and runtime evidence.

## Gate and routing

1. Run `scripts/validate_shared_pack.py --pack <project-or-pack> --report <report.json>`.
2. If the pack is absent or its design/script status is not `APPROVED`, invoke `write-visual-novel-scenario`. Stop at its design-approval and external-review consultation gates; do not invent or silently approve prose here.
3. Read [authoring-pack-mapping.md](references/authoring-pack-mapping.md) before converting or migrating script data.
4. For every PCE project, first read [current-implementation-discovery.md](references/current-implementation-discovery.md) and inspect the checked-out implementation. Never treat this skill's command examples or an older document as the engine specification.

## Integration workflow

1. For a new work, copy the checkout's official `template/template_pce_vn_cd`; do not reconstruct it. For an existing v2 scene document, use `scripts/migrate_pce_v2.py` to create a review-required shared skeleton, PCE cue map, and ambiguity report. Human approval is required before that skeleton becomes canonical.
2. Create a PCE integration mapping. Each shared cue must map explicitly to supported PCE commands or to a documented omission/substitution. Engine asset IDs and command details belong in this mapping, never in the shared cue.
3. Read [images-and-sprites.md](references/images-and-sprites.md). Use `imagegen` for original identity/outfit anchors and one master per asset. Import PNG masters through the current `pce-asset-manager.js` `importImage` path. `pack_sprite_sheet.py` may only assemble supplied transparent frames; it does not generate or retouch art.
4. Invoke `compose-pce-psg` for each original music cue, inspect the resulting version 2 file with current `inspectPsgJson`, then import with current `importPsgJson`. Author only PSG music/SFX. Do not author voice, ADPCM dialogue, or CD-DA.
5. Emit the supported normalized subset with `scripts/emit_pce_scenes.py`. Unknown entry types, conditional choices, unmapped cues, unknown mapped commands, and non-PSG audio are hard errors. Keep the source map and consumption report.
6. Run the current CD preflight, import assets, then build. CD-ROM2 CUE is required. HuCARD is optional only when requested and must receive its own preflight, build, capacity checks, and runtime QA.
7. Generate `pce-integration-manifest.json` with `scripts/build_integration_manifest.py`. Record all source/generated hashes, cue/asset mappings, consumption accounting, substitutions, target media, and verification results.
8. Follow [build-and-qa.md](references/build-and-qa.md). Verify the main path and shortest path to every ending in Geargrafx or visible GUI test play. Static reachability covers remaining histories; it is not runtime evidence.

## Non-negotiable invariants

- `pce-vn-manager.js`, `pce-asset-manager.js`, the official templates, and real preflight/build output are authoritative for the checkout being built.
- Every stable line, choice, state operation, jump, and cue use is consumed exactly once or has an explicit rejected/omitted record. Never accept normalization that silently drops data.
- Use 224x136 backgrounds for the normal message layout or 256x224 for intentional full-screen scenes. Confirm current constraints before import.
- Keep source masters and generated PCE assets hash-linked. Do not hand-edit generated binaries.
- A successful CD build says nothing about HuCARD feasibility. Validate each target independently.
- Report physical-device, display, and audio checks as external gates unless actually performed.

## Helpers

The scripts use Python 3 standard library except `pack_sprite_sheet.py`, which requires Pillow. They refuse overwrite unless `--force` is explicit. Run their tests with:

```powershell
python -m unittest discover -s "<skill-dir>\tests" -v
```
