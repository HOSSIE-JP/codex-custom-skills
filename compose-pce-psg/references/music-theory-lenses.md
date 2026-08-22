# Music theory and game-loop diagnostic lenses

These are selectable review lenses, not a universal formula for natural music. Apply only the rows relevant to the score's profile and declared intent. A finding should identify the musical location, the reason the lens applies, and a plausible counterexample. Deliberate exceptions belong in `review.waivedFindingIds`.

## Sources and application map

| Source | Useful lens | Apply to | Do not assume |
| --- | --- | --- | --- |
| [Open Music Theory: Harmonic syntax](https://openmusictheory.github.io/harmonicSyntax1.html) | A tonal phrase can move from stability through departure and dominant tension to resolution. | `tonal` phrases that declare functional harmony. | Modal, static, ambient, riff-based, or intentionally unresolved music does not need T-S-D-T or an authentic cadence. |
| [Open Music Theory: Period](https://openmusictheory.github.io/period.html) | Antecedent/consequent designs can create question/answer balance through related motives and cadential contrast. | Tonal or lyrical themes where a period is intentionally selected. | Every four- or eight-bar phrase is not a period; loops may use sentences, cells, grooves, arches, or additive form. |
| [Open Music Theory: Melodic keyboard style](https://openmusictheory.github.io/melodicKeyboardStyle.html) | Singable contour, purposeful climax, restrained leaps, and contrary/oblique bass motion can improve clarity. | Foreground tonal/modal melody and countermelody. | Action gestures, arpeggios, bass ostinati, SFX, and deliberately angular characters need not be vocal melodies. |
| [Open Music Theory: Embellishing tones](https://openmusictheory.github.io/embellishingTones.html) | Passing, neighbor, anticipation, suspension, and other non-chord tones gain meaning from metric placement and resolution. | `tonal` melody against declared chord pitches. | Chromatic notes are not automatically errors; modal color, planing, blues language, pedals, and unresolved tension may be intentional. |
| [University of Puget Sound: Voice leading](https://musictheory.pugetsound.edu/mt21c/VoiceLeading.html) | Economy of motion, voice independence, spacing, and treatment of tendency tones are useful diagnostics. | Multiple pitched parts or voiced chords where independent lines matter. | Strict species-counterpoint prohibitions are not mandatory for chip unisons, parallel planing, power intervals, pads, or deliberate fusion. |
| [Open Music Theory: Types of contrapuntal motion](https://openmusictheory.github.io/motionTypes.html) | Contrary and oblique motion can distinguish lines and reduce constant lockstep. | Melody/bass or melody/countermelody review. | Similar or parallel motion is not intrinsically unnatural; repeated chiptune layers often use it as a timbral device. |
| [Music Theory Online: 8-Bit Affordances](https://mtosmt.org/issues/mto.23.29.3/mto.23.29.3.cook.html) | Macroloops, mesoloops, microloops, recalled material, channel independence, and limited-memory form are compositional resources. | All looping PCE profiles. | Longer or less repetitive is not automatically better; short loops can fit short interactions and strong stylistic cells. |
| [Music Theory Online: Analyzing Modular Smoothness](https://www.mtosmt.org/issues/mto.19.25.3/mto.19.25.3.medina.gray.html) | Check meter, pitch, timbre, volume, and abruptness at a seam; both smoothness and disjunction can be meaningful. | Loop return and future module transitions. | A detectable seam is not automatically defective when scene change or gesture closure calls for disjunction. |
| [GDC 2019: Loop Clinic](https://gdcvault.com/play/1025942/Audio-Bootcamp-XVIII-Loop-Clinic) | Audition seamlessness and fatigue over repeated playback, not only one pass. | Human audition of loops and repeated SFX. | Static inspection can certify subjective fatigue or naturalness. |
| [Music Theory Online: motivic repetition and information density](https://mtosmt.org/issues/mto.19.25.2/mto.19.25.2.temperley.html) | Repetition supports recognition while contrast changes information density. | Motif recurrence and variation review. | A fixed optimal repetition ratio exists across tempo, genre, function, and listening duration. |

## Profile lenses

### tonal

- Declare chord pitches and, when useful, tonal function for each harmonic span.
- Check whether important strong-beat melody notes are stable or are prepared/resolved embellishments.
- Prefer purposeful contour. Review leaps over an octave and repeated large leaps; do not reject a leap solely by size.
- Review bass/melody range overlap and voice-leading cost between voiced harmonies.
- A cadence may lead into the opening rather than close absolutely; the loop must keep forward implication if that is the design.

Counterexamples: deceptive returns, chromatic mediants, pedal-point harmony, blues mixture, film-score planing, or intentionally suspended VN tension.

### modal

- Establish the center through recurrence, pedals, phrase endings, register, or accent.
- Feature characteristic scale degrees without turning every phrase into a scale exercise.
- Review whether imported functional dominant motion unintentionally erases the modal color.
- Use smooth or deliberately static voice leading, but do not require V-I.

Counterexamples: mixed modes, synthetic scales, modal interchange, and sections that intentionally destabilize the center.

### ambient

- Review spacing, rests, slow harmonic rhythm, register, timbre changes, and cumulative texture.
- Sparse onset density is valid. Warn about density only when it contradicts the brief or masks dialogue.
- Exact microloops may be acceptable inside a changing macrotexture.
- A seam can be masked through sustained state, silence, or compatible timbre rather than a tonal cadence.

Counterexamples: intentionally mechanical drones, unsettling discontinuity, dense shimmer textures, or near-silent environmental cues.

### action

- Review pulse legibility, syncopation, ostinato layering, bass/percussion coordination, and energy changes by section.
- Repetition is expected; ask whether orchestration, register, accents, or harmonic rhythm creates meso/macro variation.
- Large melodic leaps and short cells are valid. Treat them as warnings only when they undermine the declared hook.
- Preserve space for game SFX even at high energy.

Counterexamples: minimalist boss tension, slow heavy action, polyrhythmic ambiguity, or deliberately relentless single-cell loops.

### sfx-jingle

- Prefer one clearly perceived gesture with an intentional attack, contour, and release.
- Confirm `psg-sfx`, `loop: false`, short duration, and channel/noise validity.
- Pitch-language, range, repetition, and leap rules apply only when the gesture is intentionally melodic.
- Test how repeated triggering feels; a good one-shot can still become fatiguing.

Counterexamples: tonal UI confirmations, noise-only impacts, alarms, glissando-like stepped gestures, and intentionally abrasive failure sounds.

## Four-pass self-review

### Form and motif

- Can each section's function be described without referring only to its bar number?
- Does a motif recur recognizably, and are transformations recorded rather than improvised in raw events?
- After transposition or inversion, do expanded motif notes still fit the declared scale, or is chromatic departure recorded as intentional?
- Is contrast supplied by at least one meaningful dimension: pitch center, register, rhythm, density, timbre, volume, or texture?
- Does the selected form fit likely scene duration rather than an arbitrary 16-bar habit?

### Melody, harmony, and voice leading

- Is the foreground line distinguishable from accompaniment and bass?
- Are leaps, climax, repetition, chord tones, non-chord tones, and resolutions appropriate to the selected profile?
- Do simultaneous parts occupy intentional ranges? Is overlap a blend or accidental masking?
- If functional harmony is not selected, are functional-harmony warnings disabled?

### Rhythm and arrangement

- Are rests and note lengths composed, not just empty event slots?
- Are onsets excessively locked across all channels?
- For a short action loop, does repeated bass/drum grid lock create fatigue even when the overall bar signatures differ?
- Does density follow the energy curve and leave room for dialogue/game SFX?
- Do wave and volume changes support section identity without arbitrary churn?

### Loop and fatigue

- Compare the last active state and first event of every used channel.
- Listen through at least three returns when audition is available.
- Check macro/meso/micro repetition separately.
- Record an intentional discontinuity explicitly; do not hide it by waiving unrelated findings.

## Interpretation of audit output

- `technical-error`: invalid or unrepresentable data; generation should stop rather than waive it.
- `profile-warning`: a style-relative concern requiring review, correction, or an explicit waiver.
- `information`: a measured condition or deliberate-profile exception, not a failure.
- `audition: pending`: naturalness, fatigue, and actual PCE playback remain unverified regardless of static metrics.
