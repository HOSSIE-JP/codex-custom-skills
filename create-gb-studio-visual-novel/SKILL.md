---
name: create-gb-studio-visual-novel
description: Create original dialogue-heavy visual novels for GB Studio and Game Boy Color, from premise, character bible, branching plot, and Japanese dialogue through mandatory stable-ID proofreading packs, consistent ImageGen artwork, anatomy and wardrobe review, seam-resistant GBC conversion, full-width choices, and release evidence. Use for requests to make, plan, script, illustrate, revise, externally proofread, or quality-assure a new Japanese GB Studio visual novel. Use together with imagegen, build-gb-studio-game, and build-gb-studio-visual-novel; use compose-gb-studio-vn-bgm when original music is requested.
---

# Create GB Studio Visual Novel

## Goal

Create an original VN whose story, Japanese voice, branch state, character identity, artwork, GB conversion, and runtime agree. Keep authoring evidence separate from generated GB Studio resources.

## Load the relevant guidance

- Read `references/story-and-language.md` before plotting or writing Japanese dialogue.
- Read `references/external-review.md` before exporting dialogue for another AI or applying returned corrections.
- Read `references/visual-production.md` before creating character anchors, shot manifests, ImageGen prompts, or image edits.
- Read `references/gb-layout-and-release.md` before converting art, exporting, or declaring completion.
- Also use `imagegen` for raster generation and editing.
- Also use `build-gb-studio-game` and `build-gb-studio-visual-novel` for project generation, fonts, official builds, and emulator QA.
- Use `compose-gb-studio-vn-bgm` only after the scene cue plan is stable.

## Workflow

### 1. Scaffold authoritative source

Run:

```powershell
python scripts/scaffold_vn_authoring.py --out <project>\source\vn-authoring
```

Treat the copied project brief, character bible, scenario, language rules, and visual manifest as source. Do not overwrite an existing authoring pack unless the user explicitly approves `--force`.

### 2. Lock intent before prose

Define audience, duration, tone, content boundaries, cast, state variables, choice count, ending count, and required runtime paths. Calculate choice-history count as the product of option counts; never copy an unverified total into tests or documentation. Build the story in this order:

1. understandable setup;
2. inciting incident;
3. choices with short branch-specific reactions;
4. clean joins that retain state;
5. accumulated ending result.

Do not start image generation while character identity, proportions, outfit silhouettes, garment construction, branch topology, or dialogue-window policy is unsettled. Decide whether proportions are fixed or intentionally scene-dependent. Never let the generator improvise chibi, body-width, age, waist-rise, or outfit changes as a shortcut for comedy.

### 3. Write and review Japanese

Keep system UI language separate from character speech. Stage explanations as need, obstacle, tool, consequence; do not make characters recite a design document.

Run the linter during drafting and in strict mode before release:

```powershell
python scripts/lint_vn_japanese.py --scenario <scenario.json> --bible <character-bible.json> --rules <language-rules.json> --report <language-report.json>
python scripts/lint_vn_japanese.py ... --strict
```

Static checks cannot prove naturalness. Complete the read-aloud, voice, exposition, and branch-join reviews recorded in the report.

After the first complete scenario draft and before image production or generated GB Studio resources, always export the external-review pack from the authoritative JSON:

```powershell
python scripts/export_vn_review_pack.py --brief <project-brief.json> --bible <character-bible.json> --scenario <scenario.json> --out <project>\source\external-review
```

Require `01_concept.md`, `02_character_settings.md`, and `03_scenario_script.md`. The supporting `review-manifest.json` does not replace any of the three Markdown files. Fail the creation gate if a file is missing or its counts or source SHA do not match. Produce the pack even when no external reviewer is currently assigned, and regenerate it whenever the brief, bible, or scenario changes.

Do not mark manual language reviews as passed merely because lint is clean or the authoring agent reread its own output. Preserve source SHA-256 and line IDs, receive corrections as ID-addressed edits, then regenerate resources and rerun route, font, and runtime checks.

### 4. Build visual jobs from locked data

Use one source image per cut. Do not use multi-panel storyboard sheets as production masters.

```powershell
python scripts/build_vn_image_prompts.py --bible <character-bible.json> --manifest <visual-manifest.json> --out-dir <prompt-dir>
```

For every character in a cut, attach the identity anchor and exact outfit anchor to `imagegen`. Never rely on prompt-only continuity. Lock proportion mode, body silhouette, garment type and rise, exposed regions, opacity, accessories, and contrast from other cast members. Preserve the generated prompt path, reference anchors, selected source path, dimensions, SHA-256, and adoption or rejection reason in the visual manifest.

Use the default GBC-friendly style unless the user explicitly requests another style: thick dark edges, flat cel fills, two or three value steps per material, limited colors, simple background shapes, and low micro-detail. Prohibit smooth gradients, airbrush shading, bloom, translucent glow, and photorealistic texture.

### 5. Require anatomy and continuity review

Declare every visible hand and its owner, purpose, and limb connection. Hide unneeded limbs naturally in a lap, behind a prop, out of frame, or behind the body. Reject detached, duplicated, merged, or purposeless hands.

When a defect is annotated by normalized coordinates, remove that object and its connected broken anatomy. Do not reinterpret it as intended, and do not draw a replacement gesture unless explicitly requested.

Validate the manifest, converted assets, and review sheet:

```powershell
python scripts/validate_vn_visuals.py --project-root <project> --bible <character-bible.json> --manifest <visual-manifest.json> --report <visual-report.json> --review-sheet <visual-review.png> --strict
```

Visually inspect full resolution, face and hand crops, proportion and body-width consistency, garment accuracy, silhouette contrast, native 160x144 output, and runtime capture. A passing manifest is not visual proof. Reject a cut when stylization reads as unintended age drift, obesity, chibi anatomy, or wardrobe substitution relative to the locked anchors.

### 6. Implement and release through the shared GB skills

Generate stable GB Studio resources from the normalized source. Preserve the standard two-stage typewriter input, Japanese font-page contract, branch state, music transitions, and ending return flow.

For two- or three-option decisions, prefer the full dialogue-width menu layout. Add a short input-release wait before each menu so the A press that closed a preceding message or fullscreen still cannot select the first option. Verify option counts and directional links in generated resources or compiled `.MENUITEM` output, then confirm legibility and navigation with visible runtime input. Do not reduce three choices to two until a real target limitation is demonstrated.

Before per-tile palette fitting, reduce near-duplicate source colors with one shared, no-dither global palette. Assign tile palettes with neighboring-tile coherence so palette changes do not become 8x8 block noise. Treat seven GBC palettes as a hardware ceiling, not a quality target; begin with five content palettes and four title palettes when the art permits, preserve the UI band exactly, and report observed counts.

Use the exact target GB Studio version for official ROM and Web exports. Test through real input from a clean state. Wait until menu text has finished typing before navigation assertions. Compare ROM hashes, capture changed cuts in the built-in emulator, and state physical-hardware gaps. If hidden Electron or browser automation cannot retain focus, separate that harness limitation from game behavior and require a visible/manual gate instead of rewriting valid menu logic around the harness.

## Delivery contract

Report authoritative sources, the three required external-review Markdown paths and manifest SHA/counts, unresolved language reviews, image prompts and reference roles, paths and hashes, converted palette/tile metrics, official ROM/Web hashes, tested routes, and external gates.

Never claim that Japanese is natural from static lint alone, that anatomy or proportion is sound from counts alone, or that a game is playable from compilation alone.
