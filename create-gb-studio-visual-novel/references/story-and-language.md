# Story structure and natural Japanese review

## Contents

- Authoring order
- Exposition
- Branches and joins
- Character voice
- Natural Japanese review
- Self-review and independent review
- Repetition and AI-like prose
- Twist protection
- Release checklist

## Authoring order

Write a brief before dialogue. Lock intended player and rating, first-play duration, point of view, cast limit, emotional promise, state variables, ending thresholds, content boundaries, and dialogue-window capacity.

Create a beat sheet that states what the player understands after each beat. A reader should learn the world in causal order, not as a glossary. Calculate route-history count from the actual option cardinalities and enumerate every history mechanically.

## Exposition

Use this sequence for unfamiliar technology or world rules:

1. A character has a concrete desire.
2. A practical obstacle blocks it.
3. A tool or rule is introduced as a response.
4. One visible function is demonstrated.
5. A consequence or contradiction creates the next scene.

Split explanation across action and reaction. Keep system labels short and factual. Let character dialogue express opinion, misunderstanding, embarrassment, suspicion, or humor instead of repeating the UI.

Fail lines that sound like policy text, release notes, or a plot summary. Warning signs include facts both characters already know, a feature list in one speech, repeated conclusions, abstract nouns where a spoken verb is natural, and a joke explained after delivery.

## Branches and joins

Every choice arm must produce an immediate difference in wording, attitude, background, expression, state, or a later callback. Keep branch-specific responses short enough that a join remains believable. At the join, state only facts true for every arm and carry state explicitly.

For accumulated endings, enumerate all choice histories or generate them mechanically. Verify every threshold, boundary value, ending reachability, and reset path. Calculate the history count as the product of the current project's option cardinalities; for example, `2 x 3 x 2` produces 12 histories. Never copy a total from another title.

## Character voice

Record first-person pronoun, terms of address, sentence length, formality, technical vocabulary, preferred endings, avoided words, joke style, pressure response, desire, fear, and canonical voice examples.

Read one character's lines in isolation. A cast member needs a distinct concern and rhythm, not only different pronouns or sentence endings. Track when names, honorifics, and formality change; do not let intimacy appear before the relationship earns it.

## Natural Japanese review

Perform four separate passes.

### Mechanical pass

Check NFC, spaces, line endings, repeated punctuation, speaker IDs, choice labels, source SHA, and route coverage with `lint_vn_japanese.py`.

### Read-aloud pass

Read each line as speech. Shorten clauses that require rereading. Remove redundant subjects and connectors. Prefer ordinary kanji/kana balance. Split a message when the speaker would breathe or change intention, not merely at a character-count boundary.

### Voice pass

Read only one character's lines in order. Confirm pronouns, vocabulary, rhythm, humor, and emotional progression. Flag lines that could be spoken unchanged by any character.

### Exposition and join pass

Read scene transitions and every choice arm. Confirm the player has enough context before a decision, branch reactions differ, and joined dialogue does not assume one arm.

## Self-review and independent review

Record the four passes twice because they serve different purposes.

- `selfReviews` are author-owned. The authoring agent must perform them before exporting the review pack, revise the authoritative source, add concrete notes, and set each pass to `pass`. The linter reports the recorded state but never promotes it automatically.
- `manualReviews` are independent. Keep them `required` until a human or external model has reviewed the exported, SHA-matched pack and returned notes. The authoring agent's own reread cannot satisfy this gate.

After self-review, export the three-file pack, show the self-review summary and all file paths to the user, and ask whether to wait for independent review or proceed provisionally. Record the decision in `externalReviewPack.userConsultation.status`. Do not transmit files to an external service without explicit user authorization.

## Repetition and AI-like prose

Search for exact sentences and distinctive sentence tails reused across scenes. Repetition is suspicious when unrelated scenes end with the same reflective phrase, every emotional beat receives an explanatory afterthought, or narration states the theme after dialogue already showed it.

Typical failure modes:

- a poetic stock sentence appended to many scenes;
- both dialogue and narration restating the same conclusion;
- uniform sentence length and punctuation across speakers;
- excessive self-correction used as the only marker of shyness;
- a joke followed by an explanation of why it is funny;
- consent or safety language written like policy text instead of a concrete question and answer.

Use the linter's repeated-boilerplate warning as a search aid, not an automatic rewrite instruction. Judge whether repetition is an intentional motif before changing it.

## Twist protection

When the current story protects a withheld reveal, give relevant scenes an explicit phase such as `preReveal`, `reveal`, or `postReveal` and put forbidden spoiler terms in `language-rules.json`. Leave the reveal configuration empty when the story has no such device. Search narration, UI, choices, and every configured variant, not only ordinary messages.

Foreshadow with ambiguous observable details. Do not state the hidden explanation before the reveal boundary.

## Release checklist

- The premise is understandable before the first consequential choice.
- System text and character voice are distinct.
- Every speaker exists in the bible.
- Every configured variant has non-empty dialogue.
- No branch loses state at a join.
- Exact sentence reuse across scenes is intentional or revised.
- Static warnings are resolved or documented.
- All four autonomous self-review passes contain evidence and are complete before review-pack export.
- The review pack and self-review summary were presented to the user, and the user's external-review decision was recorded.
- Independent read-aloud, voice, exposition, and branch-join reviews are recorded.
