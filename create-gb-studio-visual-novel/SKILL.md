---
name: create-gb-studio-visual-novel
description: Build, illustrate, integrate, and release Japanese GB Studio visual novels from an approved engine-neutral write-visual-novel-scenario authoring pack. Use for new or migrated GB Studio VN projects that need consistent artwork, deterministic script import, Japanese fonts, hUGE BGM, official ROM/Web builds, and emulator QA. Do not use this skill to invent or approve the story or script.
---

# Create GB Studio Visual Novel

## Goal

Turn an approved shared Japanese VN authoring pack into a deterministic GB Studio project whose visible text, choices, state, semantic cues, artwork, music, generated resources, official builds, and runtime evidence agree.

## Authoring boundary

- Also use `write-visual-novel-scenario` for the premise, plot, character bible, full script, Japanese self-review, stable-ID external-review pack, corrections, and review consultation.
- If `source/vn-authoring` is missing, invoke that skill and stop at its design-approval and external-review consultation gates.
- Do not generate art or GB resources while design approval is not `APPROVED`, consultation is `pending-user-decision` or `awaiting-external-review`, any required self-review is incomplete, or recorded input hashes are stale.
- `proceeding-provisionally` permits integration, but mark every text-derived resource and build stale-on-correction and regenerate them after accepted review edits.
- Never silently reconstruct story intent from generated `.gbsres` files. Migrate an existing shared/legacy authoring pack or import manifest; otherwise report the missing authority and stop.

## Load relevant guidance

- Read `references/visual-production.md` before creating anchors, image jobs, or visual edits.
- Read `references/gb-layout-and-release.md` before conversion, generation, or release.
- Also use `imagegen`, `build-gb-studio-game`, and `build-gb-studio-visual-novel`.
- Use `compose-gb-studio-vn-bgm` only after the shared semantic cue plan is stable.

## Workflow

### 1. Validate and inventory the shared pack

Run the shared integration-ready gate before target work:

```powershell
python <write-skill>\scripts\validate_vn_scenario.py --project-root <project> --authoring-dir <project>\source\vn-authoring --report <project>\source\vn-authoring\validation-report.json --require-integration-ready
```

Record the six-input aggregate SHA. Inventory every scene, line, choice, choice option, state operation, join, ending, visual cue, music cue, and effect cue before target generation.

Copy `assets/templates/integration-manifest.json` into the project. Map every shared stable ID to a generated GB scene, event, variable, asset, font page, or declared substitution. Unknown, duplicate, or unconsumed records are errors.

### 2. Migrate existing projects deliberately

Use the shared `migrate_gb_authoring_pack.py` for the former authoring pack. If a generator-owned import manifest exists, migrate its source mappings and hashes. Do not keep two writable story authorities after migration.

When only generated GB resources exist, inspect them for an audit report but do not infer missing joins, line IDs, choice meaning, or review state.

### 3. Produce GB-specific visuals

Use one source image per production cut. Build image jobs with:

```powershell
python scripts/build_vn_image_prompts.py --bible <shared-pack>\character-bible.json --manifest <gb-visual-manifest.json> --out-dir <prompt-dir>
```

Before generating any character artwork, invoke `ai-character-reference-reconstructor` to create the character's identity anchor sheets from the character images attached to the current request. Do not substitute local project images, prior conversation images, or inferred character settings for the required attached references; if no usable character image is attached, stop image generation and request one. Use the completed reference sheets as the fixed visual authority for `imagegen`, attach the identity and exact outfit anchors to every relevant image job, preserve the selected project-bound source, and record prompt, inputs, hash, adoption or rejection reason, crop policy, and runtime capture.

Generate deterministic text, logos, title elements, and UI with the project-native pipeline rather than raster image generation. Preserve the GBC native-size, palette, tile, anatomy, identity, garment, and silhouette checks in the visual references.

### 4. Generate GB Studio resources from shared IDs

Use `build-gb-studio-visual-novel` to normalize the shared script into GB segments, stable events, variables, fonts, portraits, choices, joins, and endings. Preserve full source consumption even when GB scene splitting differs from the shared graph.

Keep speaker-label, typewriter, input-release, portrait-state, still-state, font-page, and ending-return policies in the GB integration manifest. Record every audio or effect substitution; silence without an intentional-silence cue is a missing conversion.

### 5. Compose and integrate BGM

Translate shared music cues to `compose-gb-studio-vn-bgm` cue records. Register every generated MOD through the project authority and test start, stop, loop, carryover, replacement, and intentional silence. Do not copy an unregistered file and call it integrated.

### 6. Validate and release

Run visual validation, then prove exact shared-ID consumption:

```powershell
python scripts/validate_vn_visuals.py --project-root <project> --bible <shared-pack>\character-bible.json --manifest <gb-visual-manifest.json> --report <visual-report.json> --review-sheet <visual-review.png> --strict
python <write-skill>\scripts\validate_integration_manifest.py --project-root <project> --authoring-dir <project>\source\vn-authoring --manifest <gb-integration-manifest.json> --report <integration-report.json>
```

Then apply the exact-version editor, font-byte, palette/tile, metasprite, official ROM/Web, hash, and built-in-emulator gates from the two GB build skills. Static graph validation covers every shared route. Runtime playthrough covers the declared main route and the shortest route to every ending, including menu boundaries and return/reset behavior.

## Completion contract

Report the shared aggregate SHA and review state, integration-manifest consumption counts, substitutions, visual source and runtime evidence, font and palette/tile metrics, registered BGM cues, official ROM/Web hashes, tested main/ending routes, and physical-device gaps.

Never claim story approval from this skill, Japanese naturalness from lint, visual correctness from metadata, resource integration from file presence, or playability from compilation alone.
