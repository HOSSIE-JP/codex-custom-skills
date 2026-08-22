# Japanese language and review

## Drafting

- Separate system/UI wording, narration, internal thought, and spoken voice.
- Let dialogue perform an action: evade, test, comfort, provoke, conceal, negotiate, or decide. Remove explanations that neither alter understanding nor relationship.
- Stage necessary exposition as need, obstacle, attempted solution, and consequence. Do not make characters recite the design document.
- Define each speaker's sentence length, first-person form, terms of address, formality, rhythm, avoidance habits, and pressure response in the bible. Exceptions need scene-specific intent.
- At joins, acknowledge meaningful prior choices without replaying the whole branch. Do not erase state that the ending depends on.

## Four mandatory self-review passes

Each pass must end with `status: "complete"`, evidence of what was inspected, concrete revisions, and remaining concerns in `self-review.json`.

1. `mechanical`: schema, graph, IDs, punctuation, spelling, placeholders, repetitions, speaker validity.
2. `readAloud`: spoken rhythm, breath, tongue-twisters, ambiguous reference, unnatural written-language cadence. This is a performed/manual pass.
3. `characterVoice`: compare every speaker against the bible, especially under pressure and around joins.
4. `expositionAndBranchJoins`: remove redundant explanations; verify choice reactions, retained state, joins, and ending causality.

Static lint can find candidates; it cannot certify naturalness, dramatic effectiveness, or character truth. Preserve `automatedNaturalnessClaim: false` in reports.

## External review decision

Always create the three local Markdown files and manifest after self-review. The exporter calculates a recommendation from duration, ending count, dialect, specialized facts, sensitive topics, and unresolved concerns. Recommendation does not replace user consultation.

Allowed consultation statuses are `pending-user-decision`, `awaiting-external-review`, `proceeding-provisionally`, `waived-by-user`, and `complete`.

Creating local files is not permission to upload or send them. Immediately before any external transmission, obtain explicit user authorization and record the destination and authorized scope outside the canonical story data.

Request returned prose changes as stable-ID records: `id`, `field`, `before`, `after`, and `reason`. Structural proposals—new branches, facts, state, cues, or endings—must be reviewed separately and manually incorporated into a new design revision.
