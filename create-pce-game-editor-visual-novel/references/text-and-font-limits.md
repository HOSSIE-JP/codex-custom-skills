# Text and font limits

Two build-blocking text constraints are easy to hit one character/message at a time through the real build preflight, which stops enumerating after the first bad item per pass. Scan the whole script up front instead.

## Font coverage: System Card jp-v3 is JIS Level 1 only

The System Card `jp-v3` font covers JIS X 0208 rows 1-8 and 16-47 — kana/symbols plus *only JIS Level 1* kanji. Level 2 kanji fail the build with `System Card jp-v3 font does not contain U+XXXX` from `inspectVnSceneDocumentBuild`.

Level-2 characters actually hit in one script (ordinary vocabulary, nothing exotic), all fixed with no loss of meaning:

| Level-2 (rejected) | Replacement |
| --- | --- |
| 褪せた | 古びた / あせた |
| 埃 | ほこり |
| 譫言 | うわ言 |
| 皺 | しわ |
| 掠れる | かすれる |
| 頷き | うなずき |
| 錆びついて | さびついて |
| 軋んだ | きしんだ |
| 呟く | つぶやく |
| 炙られた | 焼かれた |
| 橙色 | 赤く |

### Scan up front instead of iterating build errors

```js
const { normalizeSystemCardText, isJapaneseV3GlyphBytes } = require('<checkout>/pce-system-card-font.js');
const iconv = require('<checkout>/node_modules/iconv-lite'); // transitive dependency, already installed

for (const char of uniqueCharacters) {
  const normalized = normalizeSystemCardText(char);
  const buf = iconv.encode(normalized, 'Shift_JIS');
  if (!isJapaneseV3GlyphBytes(buf)) flagged.push(char);
}
```

See `scripts/scan_text_budget.js`, which runs this scan and the display-budget scan below together in one report.

## Display budget: 68 glyph-entries, not the 96-char raw-storage cap

The real per-message display budget is **68 glyph-entries** (17 chars × 4 lines) — not the 96-character raw-storage cap that `normalizeMessageCommand`/`resolveMessageText` silently truncates to. The 68-entry budget is enforced only at build/encode time, via `encodeSystemCardText(display.full, location, {maxCharacters: 68})`, where:

- `display.full = speakerDisplayName + '：\n' + text` for a named speaker — the speaker name costs `len(displayName) + 2` entries;
- `display.full = text` with **zero prefix cost** for an empty/`narrator` speaker;
- each literal `\n` in `text` also counts as one entry.

There is **no automatic line-wrapping anywhere in the pipeline** — authors must manually decide where a message breaks. A message that passes the 96-char raw-storage check can still fail this stricter 68-entry check once the speaker prefix and any `\n`s are counted.

Confirmed for `message` commands specifically. Choice labels (`choice.choices[].label`) and `spritetext` render through the same font but were **not** confirmed against the same 68-entry cap — verify independently before assuming it applies unchanged.

### Scan up front instead of iterating build errors

Call `encodeSystemCardText` with a high `maxCharacters` (e.g. 9999) so it never throws, then measure `.length` on the result for every message using the `display.full` formula above. Flag every message over 68 in one pass.

**Fix**: split an over-budget message into two sequential message entries at a natural sentence boundary. No semantic content lost, no manual `\n` wrapping needed.

## `scripts/scan_text_budget.js`

A committed Node helper that runs both scans against an emitted PCE scene document in one pass, printing every offending character and every over-budget message in a single report. See below and the script's own `--help`.
