# Deterministic visual-novel imports

## Normalize before generating

Treat the source project and its referenced asset manifests as immutable input. Parse source-specific structures into a small intermediate representation with explicit records for:

- background and event-still changes;
- portrait show, hide, expression, position, flip, and movement;
- message, speaker, narration, and text timing;
- choice, label, input check, jump, timeout, and join;
- music, voice, effect, wait, and screen effect.

Attach source scene ID and command index to every normalized command. Maintain a source-command count by type. Reject unknown commands during normalization; never allow the emitter to ignore them.

## Stable generation

Derive scene, event, actor, variable, asset, and symbol IDs from semantic keys with one stable algorithm. Keep IDs unchanged when unrelated source content moves.

Split target scenes at background changes when required by GB Studio. A generated segment must receive the complete visual state at its entry: current background, event-still mode, portrait expressions and visibility, music, and other persistent state. Branch-only source scenes without a new background inherit their predecessor state.

Create fresh event objects and IDs in every generated branch. Validate:

- every jump and switch target exists;
- every choice arm has a target and reaches an intended join or terminal;
- every required segment is reachable from boot;
- every actor reference belongs to its scene;
- every variable, font, sprite, background, sound, and song reference exists;
- every source command is consumed exactly once.

## Presentation translation

Resize GBC-only backgrounds to 160 pixels wide first, then crop or compose for the dialogue region. Keep source masters separate. Measure the official build before reducing source detail for a presumed tile limit.

Convert unsupported full standing art to face or bust portraits. Preserve expression state across messages, limit overlapping portraits by scanline usage, and suppress all portraits while an event still is active.

Translate unsupported audio deliberately:

- voice clips to speaker-specific text tones when full voice is out of scope;
- streaming or CD title audio to a named supported BGM;
- event-still audio to a short supported jingle;
- source effects to supported tone, beep, crash, or generated sound resources.

Record the source cue, replacement resource, reason, and timing behavior. Silence without a manifest entry is a missing conversion.

## Import manifest

Write one machine-readable manifest next to the project. Use paths relative to the project root. Include at least:

- format version, source project, source-of-truth files, target GB Studio version and hardware settings;
- dialogue presentation policy, including the speaker-label format and whether narration is unlabeled;
- source and generated scene counts;
- source, consumed, and generated command counts by type;
- message and choice records with source location and generated event or scene key;
- font pages, assignments, safe codes, reserved codes, resource IDs, and hashes;
- backgrounds, portraits, expressions, music, sounds, and substitutions;
- scene segments, branch targets, joins, and reachability result;
- SHA-256 for every authoritative source and generated release artifact;
- validation status, failures, and explicitly untested external gates.

For text validation, keep these stable fields:

```json
{
  "dialogueRuntime": {
    "speakerLabelFormat": "【{speaker}】",
    "narrationSpeakerLabel": false
  },
  "statistics": {"messages": 0, "choices": 0},
  "messages": [
    {
      "eventId": "uuid",
      "speaker": "話者",
      "sourceText": "本文",
      "generatedText": "【話者】\n本文",
      "fontPage": 0
    }
  ],
  "fontPages": [
    {"page": 0, "fontId": "uuid", "compiledFontIndex": 1}
  ]
}
```

`compiledFontIndex` may be omitted only when the project intentionally uses `page + 1`. Record the assumption in validation output.

## Validation layers

Run validation in this order:

1. normalized source inventory and unknown-command rejection;
2. generator counts, IDs, references, graph reachability, joins, and full consumption;
3. source-versus-generated normalized visible text;
4. font page and compiled-byte validation;
5. background, portrait, palette, tile, and scanline validation;
6. target-version editor inspection in a disposable copy;
7. official ROM and Web builds, warnings, timestamps, headers, and hashes;
8. focused runtime paths for changed behavior;
9. full playthrough and physical hardware only when they remain in the assigned scope.

Use temporary direct-start scenes or debugger state only after normal boot and input have already been proven. Keep acceleration out of release data and record every override.
