---
name: write-visual-novel-scenario
description: Create, revise, migrate, and independently review engine-neutral Japanese visual-novel briefs, plots, branching scenario designs, normalized scripts, semantic presentation cues, and stable-ID review packs. Use before GB Studio or PCE Game Editor integration; do not use for engine assets, builds, image generation, or music production.
---

# Write Visual Novel Scenario

Create the canonical Japanese story source in `source/vn-authoring/`. Downstream GB Studio and PCE skills consume it; they do not rewrite story intent.

## Load only what the work needs

- Read [references/story-craft-and-sources.md](references/story-craft-and-sources.md) before choosing a plotting method or drafting a scenario design.
- Read [references/design-review-schema.md](references/design-review-schema.md) before populating or validating the four-file design-review subset.
- Read [references/japanese-language-and-review.md](references/japanese-language-and-review.md) before dialogue, self-review, external review, or corrections.
- Read [references/schema-and-workflow.md](references/schema-and-workflow.md) when validating a completed script, migrating, or handing the pack to an engine skill.

## Workflow

1. Scaffold with `python scripts/scaffold_vn_authoring.py --project-root <project> --out <project>/source/vn-authoring`. Never use `--force` without explicit overwrite approval.
2. Normalize the request in `project-brief.json` and `character-bible.json`. Do not inherit genre, cast, rating, routes, relationships, or style from another work.
3. Compare applicable craft lenses, record selected and rejected alternatives, then write character change, beats, branch causality, joins, endings, duration, and semantic cue intent in `scenario-design.json`.
4. Set the design to `REVIEW_REQUIRED`, run `validate_vn_design.py`, and stop for human review. A passing design-only report is the correct result at this stage; `script.json` and `self-review.json` are not required yet. Only the user or an authorized reviewer may advance the same revision to `APPROVED`.
5. After approval, write `script.json` with the same revision. Give every scene, entry, choice option, cue, and ending a persistent semantic ID; never derive review IDs from array positions. Semantic cues must not contain asset IDs, dimensions, formats, filenames, or engine commands.
6. Only after the script exists, run the full `validate_vn_scenario.py` and `lint_vn_japanese.py`. Revise through four evidenced passes: mechanical, read-aloud, character voice, and exposition/branch joins. Static lint never proves naturalness.
7. Export the local review pack. Report its risk recommendation and ask whether to wait, proceed provisionally, waive review, or record completion. Never transmit files externally without explicit authorization immediately before transmission.
8. Apply returned prose corrections by stable ID only. Reject stale hashes, mismatched before-text, duplicate edits, structural changes disguised as prose, or paths outside the project root.
9. Before any downstream engine integration, require `--require-integration-ready`. `APPROVED` alone is insufficient: aggregate self-review and all four passes need complete status, evidence, and revision records; external-review status must be `proceeding-provisionally`, `waived-by-user`, or `complete`.

## Commands

```powershell
python scripts/validate_vn_design.py --project-root <project> --authoring-dir <project>/source/vn-authoring --report <project>/source/vn-authoring/design-report.json
python scripts/validate_vn_scenario.py --project-root <project> --authoring-dir <project>/source/vn-authoring --report <project>/source/vn-authoring/validation-report.json
python scripts/validate_vn_scenario.py --project-root <project> --authoring-dir <project>/source/vn-authoring --report <project>/source/vn-authoring/integration-ready-report.json --require-integration-ready
python scripts/lint_vn_japanese.py --project-root <project> --authoring-dir <project>/source/vn-authoring --report <project>/source/vn-authoring/language-report.json --strict
python scripts/export_vn_review_pack.py --project-root <project> --authoring-dir <project>/source/vn-authoring --out <project>/source/external-review
python scripts/apply_review_corrections.py --project-root <project> --authoring-dir <project>/source/vn-authoring --manifest <project>/source/external-review/review-manifest.json --corrections <corrections.json>
python scripts/migrate_gb_authoring_pack.py --project-root <project> --source <old-pack> --out <project>/source/vn-authoring
python scripts/validate_integration_manifest.py --project-root <project> --authoring-dir <project>/source/vn-authoring --manifest <integration-manifest.json>
```

## Completion contract

Deliver design-only evidence before approval, then canonical paths and aggregate SHA, design revision/status, full graph and language reports, structural choice-history count, reachable endings, four-pass evidence, three review Markdown files, risk recommendation, consultation status, and unresolved concerns. Keep physical play, generated art/audio, engine integration, and runtime QA as downstream gates.
