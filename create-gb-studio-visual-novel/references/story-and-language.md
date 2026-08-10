# Story structure and natural Japanese review

## Contents

- Authoring order
- Exposition
- Branches and joins
- Character voice
- Natural Japanese review
- Twist protection
- Release checklist

## Authoring order

Write a brief before dialogue. Lock intended player and rating, first-play duration, point of view, cast limit, emotional promise, state variables, ending thresholds, content boundaries, and dialogue-window capacity.

Create a beat sheet that states what the player understands after each beat. A reader should learn the world in causal order, not as a glossary.

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

Every choice arm must produce an immediate difference in wording/attitude, background/expression, state, or a later callback. Keep branch-specific responses short enough that a join remains believable. At the join, state only facts true for every arm and carry state explicitly.

For accumulated endings, enumerate all choice histories or generate them mechanically. Verify every threshold and boundary value.

## Character voice

Record first-person pronoun, terms of address, sentence length, preferred endings, formality, technical vocabulary, avoided words, joke style, pressure response, and canonical voice examples.

Do not reduce gender or identity variation to pronoun substitution. Give variant lines a distinct concern or self-perception while preserving equal agency and ending access.

## Natural Japanese review

Perform four separate passes.

### Mechanical pass

Check NFC, spaces, line endings, repeated punctuation, speaker IDs, choice labels, and route coverage with `lint_vn_japanese.py`.

### Read-aloud pass

Read each line as speech. Shorten clauses that require rereading. Remove redundant subjects and connectors. Prefer the kanji/kana balance a speaker would naturally use; do not replace ordinary kanji with awkward partial hiragana merely to look simple.

### Voice pass

Read only one character's lines in order. Confirm pronouns, vocabulary, rhythm, humor, and emotional progression. Flag lines that could be spoken unchanged by any character.

### Exposition and join pass

Read scene transitions and every choice arm. Confirm the player has enough context before a decision, branch reactions differ, and joined dialogue does not assume one arm.

Record review status as evidence. An automated report must leave these passes as `required` until a reviewer sets them to `pass` with a note.

## Twist protection

Give scenes an explicit reveal phase such as `preReveal`, `reveal`, or `postReveal`. Put forbidden spoiler terms in `language-rules.json`. Search narration, UI, choices, and every gender variant—not only ordinary messages.

Foreshadow with ambiguous observable details. Do not state the hidden explanation before the reveal boundary.

## Release checklist

- The premise is understandable before the first consequential choice.
- System text and character voice are distinct.
- Every speaker exists in the bible.
- Every configured variant has non-empty dialogue.
- No branch loses state at a join.
- Static warnings are resolved or documented.
- All four natural-language reviews are recorded as passed.
