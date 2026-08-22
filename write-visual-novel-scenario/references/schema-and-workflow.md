# Canonical pack schema and workflow

## Authoritative files

`source/vn-authoring/` contains:

- `project-brief.json`: Japanese-only scope, audience, duration, branching expectations, content boundaries, review status, and review-risk inputs.
- `character-bible.json`: stable character IDs, exact age or explicit age category, role, desire, obstacle, change, relationships, address terms, and voice constraints.
- `scenario-design.json`: revision, `REVIEW_REQUIRED` or `APPROVED`, selected/rejected structure lenses, beats, scene boxes, branches, joins, endings, and cue plan.
- `script.json`: normalized executable narrative intent, not an engine command stream.
- `language-rules.json`: allowed speakers and mechanical Japanese checks.
- `self-review.json`: evidence for all four human/agent passes.

Generated reports are evidence, not source. `source/external-review/` is a regenerable local projection.

## Stable IDs and flow

IDs use lowercase ASCII segments separated by `.`, `_`, or `-`. Preserve them across reordering and prose revision. Use role-based names such as `scene.arrival`, `line.arrival.warning`, `choice.arrival.enter`, and `ending.trust`; do not use array numbers or display text as identity. Option IDs and non-visible entries are stable too.

`script.json` uses `revision`, `status`, `startSceneId`, `stateVariables`, `cues`, `endings`, and `scenes`. A scene has `entries` and optional `nextSceneId`. Entries are only `line`, `choice`, `jump`, `state`, or `cue`. A terminal choice or jump supplies its own scene targets; ending scenes have no outgoing edge and are identified by `endings[].sceneId`. A choice option may set declared state. Conditions may read declared state. State entries use `{id,type:"state",variableId,operation,value}` with optional integer bounds. Engine commands and assets do not belong here.

Semantic cues contain `id`, `kind`, `emotion`, `narrativePurpose`, `characters`, `visibleContent`, `musicFunction`, and `playbackIntent`. `playbackIntent` is `start`, `continue`, `stop`, or `not-applicable`. Cue entries use `{id,type:"cue",cueId}`. Asset IDs, filenames, dimensions, formats, engine names, and engine commands are rejected.

## Gates

1. Design remains `REVIEW_REQUIRED` until the recorded revision is approved.
2. Script drafting begins only from that approved revision; script `revision` and `status` must match.
3. Graph/language checks and all four self-review passes precede review-pack export.
4. External-review consultation is mandatory; transmission is separately authorized.
5. Any canonical source change makes the aggregate review SHA stale. Regenerate the pack and reject corrections addressed to an older aggregate.
6. Downstream integration consumes every line, choice, state/cue entry, cue definition, and ending exactly once, or records an explicit substitution. It may split scenes or substitute assets, but visible lines, choice meaning, state, joins, and endings remain traceable by shared ID.

## Migration

`migrate_gb_authoring_pack.py` performs a one-way conversion from an older GB authoring pack containing source JSON. It preserves valid existing IDs and assigns content-derived IDs once where absent. It sets design and script back to `REVIEW_REQUIRED`, resets self-review, and reports lossy or ambiguous legacy commands. It refuses to infer author intent from a generated `.gbsres` alone.
