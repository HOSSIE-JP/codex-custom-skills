# PCE high-level score schema version 2

The score is the editable source of truth. `scripts/compose-pce-psg.js` validates and normalizes it, expands motifs and note durations, derives HuC6280 periods, and writes the import asset and audits. Unknown fields are rejected.

## Root

| Field | Requirement |
| --- | --- |
| `schemaVersion` | Integer `2`. PCE Game Editor output separately remains document version 2. |
| `id` | 1-48 ASCII letters, numbers, `_`, or `-`. |
| `name` | Non-empty display name, at most 128 characters. |
| `type` / `loop` | `psg-song` with `true`, or `psg-sfx` with `false`. |
| `intent` | Purpose, emotion, scene function, energy/tension curve, and hardware targets. |
| `styleProfile` | `tonal`, `modal`, `ambient`, `action`, or `sfx-jingle`. |
| `transport` | Tempo, meter, fixed resolution, bars, speed, and complete-asset loop metadata. |
| `tonality` | Tonic, mode/scale name, and optional scale labels. Required for new work. |
| `form` | Ordered, non-overlapping sections covering every bar. |
| `harmony` | Ordered chord/pitch-center spans; may be empty outside tonal work. |
| `motifs` | Reusable interval/rhythm cells. |
| `parts` | Fixed-channel musical roles and their note or motif occurrences. |
| `mix` | Channel count, master volume, default wave/period, and density intent. |
| `review` | Audition state, four pass records, notes, and intentional finding waivers. |

## Intent and profiles

```json
{
  "intent": {
    "purpose": "Dialogue BGM",
    "emotion": ["warm", "uncertain"],
    "sceneFunction": "Support conversation without masking it",
    "energyCurve": ["A:low", "B:medium"],
    "tensionCurve": ["A:stable", "B:return"],
    "hardwareTargets": ["both"]
  },
  "styleProfile": "tonal"
}
```

`hardwareTargets` accepts `generic`, `cdrom2`, `hucard`, or `both`. This records intent; integration still validates each target separately.

## Transport

```json
{
  "transport": {
    "bpm": 108,
    "timeSignature": "4/4",
    "resolution": 4,
    "bars": 4,
    "speed": 6,
    "loop": {
      "enabled": true,
      "startStep": 0,
      "endStep": 64,
      "intentionalDiscontinuity": false
    }
  }
}
```

- BPM: 30-300.
- `resolution` is exactly 4: one score step is a 16th note relative to a quarter-note beat.
- Derived total steps must be 1-4096.
- PCE songs loop over the complete asset; partial loop ranges are rejected.
- True swing, triplets, variable step duration, microtonality, and continuous pitch bend are not supported.

## Tonality, form, and harmony

```json
{
  "tonality": {
    "tonic": "C",
    "mode": "major",
    "scale": ["C", "D", "E", "F", "G", "A", "B"]
  },
  "form": [{
    "id": "A",
    "name": "A",
    "startBar": 1,
    "endBar": 2,
    "function": "stable opening",
    "energy": 0.25,
    "tension": 0.2
  }],
  "harmony": [{
    "step": 0,
    "duration": 16,
    "symbol": "C",
    "function": "T",
    "pitches": ["C3", "E3", "G3"]
  }]
}
```

Energy and tension are numbers from 0 through 1. Harmony pitches include octaves so voice-leading and strong-beat analysis can use actual register. A modal or ambient score may leave `harmony` empty, but must still describe its pitch center or scale in `tonality`.

## Motifs and transformations

```json
{
  "motifs": [{
    "id": "answer",
    "intervals": [0, 2, 4],
    "rhythm": [1, 1, 2],
    "description": "rising answer"
  }]
}
```

Intervals are semitones relative to the occurrence root. Rhythm values are positive step durations. A motif occurrence may use:

- `transpose`: semitones;
- `octave`: octave displacement;
- `inversion`: invert interval signs around the root;
- `rhythmScale`: integer multiplier;
- `fragmentStart` and `fragmentLength`.

The occurrence `duration` must equal the transformed fragment's total duration. The normalized score records the motif reference and transformation; the PSG pattern contains the expanded notes.

## Parts and events

Pitched part:

```json
{
  "id": "melody",
  "role": "melody",
  "channel": 0,
  "range": { "min": "C4", "max": "C6" },
  "wave": 45,
  "volume": 18,
  "events": [
    {
      "step": 0,
      "duration": 4,
      "note": "C4",
      "articulation": "normal"
    },
    {
      "step": 8,
      "duration": 4,
      "note": "C5",
      "motifRef": "answer",
      "transform": {
        "transpose": 0,
        "octave": 0,
        "inversion": false,
        "rhythmScale": 1,
        "fragmentStart": 0,
        "fragmentLength": 3
      },
      "articulation": "legato"
    }
  ]
}
```

Noise part:

```json
{
  "id": "percussion",
  "role": "percussion",
  "channel": 4,
  "noise": true,
  "volume": 7,
  "events": [
    { "step": 0, "duration": 1, "noisePeriod": 7, "articulation": "staccato" }
  ]
}
```

- Roles: `melody`, `countermelody`, `harmony`, `arpeggio`, `pad`, `bass`, `percussion`, or `accent`.
- Channels are fixed 0-5. Noise uses 4 or 5.
- `mix.channels` is the highest usable channel index plus one, not the number of active parts. A sparse allocation using channels 0, 1, 2, and 5 therefore requires `mix.channels: 6`.
- Note names use forms such as `C4`, `F#3`, `Bb2`, or `C-1`. MIDI note 0-127 is also accepted.
- If both `note` and `midi` are present, they must agree. If `period` is also present, it must equal the calculated period.
- Event volume is 0-31; wave is 0-45.
- Articulation is `normal`, `legato`, `staccato`, or `tenuto`. Duration creates a deterministic volume-zero note-off; a reattack at the same step wins.
- Notes on one channel may touch at their boundaries but may not overlap. The generator never performs hidden voice stealing.
- The expanded pattern may contain at most 2048 events.

## Mix and review

```json
{
  "mix": {
    "channels": 5,
    "masterVolume": 90,
    "defaultWave": 45,
    "fallbackPeriod": 428,
    "densityTarget": "dialogue-light"
  },
  "review": {
    "audition": "pending",
    "notes": [],
    "passes": {
      "formMotif": { "status": "complete", "notes": "A/B contrast reviewed." },
      "melodyHarmony": { "status": "complete", "notes": "Leaps and resolutions reviewed." },
      "rhythmArrangement": { "status": "complete", "notes": "Dialogue space retained." },
      "loopFatigue": { "status": "complete", "notes": "Static seam review complete." }
    },
    "waivedFindingIds": []
  }
}
```

Review status accepts `pending` or `complete`. A profile warning remains visible when waived. Audition must remain pending until actual listening occurs.

`mix.densityTarget` is a short authoring label with a maximum of 64 characters; put longer reasoning in `intent` or `review.notes`.

## Determinism, hashes, and import output

Generation writes canonical LF-terminated JSON. The normalized score SHA is embedded in new PSG documents and both score/PSG hashes appear in the audit. Use `verify-pce-psg-artifacts.js` after any edit.

The PSG file contains exactly one PCE Game Editor version 2 asset. Pattern events contain `step`, `channel`, `period`, `volume`, and either `wave` or `noise`, plus optional note metadata. The PCE serializer currently uses 8 bytes per pattern event; the audit reports this byte budget.

## Schema version 1

Do not manually add musical meaning to old period/event data. Use `migrate-pce-psg-score.js`. Migration creates `legacyExact` parts, preserves old output bytes, sets style and tonality to null, and limits audit conclusions to technical structure.
