# Design-review field contract

Use this four-file subset before `script.json` exists. Run `validate_vn_design.py`; do not run the full scenario validator or Japanese script linter at this gate.

## `project-brief.json`

- `formatVersion`: `2`
- `projectId`: populated stable project ID; identical to bible and design
- `language`: `ja`
- `expectedMinutes`: numeric target; must equal the sum of scene-box minutes
- `branching.choiceCount`, `branching.endingCount`: exact counts of design choice and ending plans
- `branching.stateVariables`: stable IDs or objects containing `id`

## `character-bible.json`

- `projectId`: same as brief
- `characters[].id`: stable and unique
- A character is major when `major: true`, `importance` is `major`, `main`, or `protagonist`, or `role` says `主人公`/`主要`. If none are explicitly marked, every listed character is treated as major.
- Every major character needs `desire`, `obstacle`, an intended `change`/`arc`/`changeArc`/`transformation` (explicit constancy is valid), and non-empty `voice` guidance. These may be supplied in the matching `scenario-design.characterArcs[]` except voice, which remains canonical in the bible.
- `language-rules.allowedSpeakers` must equal `narrator` plus all character IDs.

## `scenario-design.json`

- `revision`: positive integer
- `status`: `REVIEW_REQUIRED` with `approvedRevision: null`, or `APPROVED` with `approvedRevision` equal to `revision`
- `structureLensCandidates`: at least two objects with stable `id`. A selected candidate records `selectionReason`, `fitReason`, `decisionReason`, or `reason`; every rejected candidate records `rejectionReason`, `reasonNotSelected`, or `decisionReason`.
- `selectedStructureLenses`: one or more candidate IDs, or objects containing `id`/`lensId` and an optional reason. Keep at least one rejected alternative.
- `beats`: non-empty objects with stable unique `id`.
- `sceneBoxes`: non-empty objects with stable unique `id` and non-negative `estimatedMinutes` or `minutes`.
- `branchAndJoinPlan`: choice objects use `type: "choice"` (or `kind`), stable `id`/`choiceId`, optional `sceneId`, and at least two options. Each option has stable `id`, visible intent/text as needed, and a `targetSceneId`; state effects use `setState` or declared `stateReads`/`stateWrites`.
- `endingPlan`: objects with stable unique `id` and a valid `sceneId`.
- All `*SceneId` references must resolve to `sceneBoxes[].id`; all state references must resolve to `project-brief.branching.stateVariables`.
- `semanticCuePlan`: stable unique `id` plus meaning-level emotion, narrative purpose, characters, visible content, music function, and playback intent. Nested asset IDs, file/path, resolution/dimensions/width/height, format, engine, and command fields are forbidden.

Passing this contract means the design is internally reviewable. It does not approve the design, prove Japanese dialogue quality, or authorize script, asset, or engine production.
