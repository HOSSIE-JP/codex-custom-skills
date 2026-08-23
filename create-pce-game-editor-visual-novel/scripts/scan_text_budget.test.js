#!/usr/bin/env node
'use strict';

/**
 * Tests scan_text_budget.js's own orchestration/grouping logic only —
 * against a small stub font module, NOT the real checkout's actual
 * encoding correctness. The live checkout stays authoritative; if its real
 * pce-system-card-font.js behavior ever diverges from these stubs, that is
 * not a bug in this test. Run against the real checkout (see
 * references/text-and-font-limits.md) to validate real scripts.
 *
 * Plain assertions, no framework — matches compose-pce-psg's *.test.js
 * convention. Run with: node scan_text_budget.test.js
 */

const assert = require('assert');
const { scanScenes, displayFull } = require('./scan_text_budget.js');

// A small stub standing in for pce-system-card-font.js: only 'A', 'B', 'C',
// and '\n' are "in the font"; anything else is treated as a rejected glyph.
// This is deliberately unrelated to real JIS coverage — it only needs to be
// deterministic so the scanner's grouping/threshold logic can be asserted.
const ALLOWED = new Set(['A', 'B', 'C', '\n']);

const stubFontModule = {
  normalizeSystemCardText(str) {
    return str;
  },
  isJapaneseV3GlyphBytes(buf) {
    const ch = buf.toString('utf8');
    return ALLOWED.has(ch);
  },
  encodeSystemCardText(full) {
    // One "entry" per character, matching the real \n-counts-as-one-entry rule.
    return { length: full.length };
  },
};

const stubIconv = {
  encode(str) {
    return Buffer.from(str, 'utf8');
  },
};

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (err) {
    console.error(`not ok - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

test('displayFull: named speaker costs len(displayName) + 2 entries via the "：\\n" prefix', () => {
  assert.strictEqual(displayFull('香月 美咲', 'AB'), '香月 美咲：\nAB');
});

test('displayFull: empty/narrator speaker has zero prefix cost', () => {
  assert.strictEqual(displayFull('', 'AB'), 'AB');
  assert.strictEqual(displayFull('narrator', 'AB'), 'AB');
});

test('scanScenes: flags a character rejected by the font module, grouped with its location', () => {
  // ASCII is always skipped from font-coverage checks (mirrors real jp-v3
  // coverage), so the "rejected" stand-in must be non-ASCII to exercise
  // the check at all — 'あ' is not in the stub's ALLOWED set.
  const doc = {
    scenes: [
      {
        id: 'scene_one',
        commands: [
          { type: 'message', speaker: '', text: 'AあB' },
        ],
      },
    ],
  };
  const { fontViolations, displayViolations } = scanScenes(doc, { fontModule: stubFontModule, iconv: stubIconv, maxDisplay: 68 });
  assert.strictEqual(fontViolations.length, 1);
  assert.strictEqual(fontViolations[0].char, 'あ');
  assert.strictEqual(fontViolations[0].locations[0].sceneId, 'scene_one');
  assert.strictEqual(fontViolations[0].locations[0].commandIndex, 0);
  assert.strictEqual(displayViolations.length, 0);
});

test('scanScenes: a clean short message with only ASCII produces no violations', () => {
  const doc = {
    scenes: [
      { id: 'scene_three', commands: [{ type: 'message', speaker: '', text: 'ABC' }] },
    ],
  };
  const { fontViolations, displayViolations } = scanScenes(doc, { fontModule: stubFontModule, iconv: stubIconv, maxDisplay: 68 });
  assert.strictEqual(fontViolations.length, 0);
  assert.strictEqual(displayViolations.length, 0);
});

test('scanScenes: display-budget math includes the speaker-prefix cost even when under the char cap otherwise', () => {
  // The "：\n" prefix itself also triggers font-coverage checks on those two
  // characters (irrelevant to this test — only displayViolations is asserted).
  const speaker = 'S'.repeat(3); // "SSS" + "：\n" = 5 entries prefix
  const text = 'A'.repeat(65);
  const doc = {
    scenes: [
      { id: 'scene_four', commands: [{ type: 'message', speaker, text }] },
    ],
  };
  const { displayViolations } = scanScenes(doc, { fontModule: stubFontModule, iconv: stubIconv, maxDisplay: 68 });
  assert.strictEqual(displayViolations.length, 1);
  assert.strictEqual(displayViolations[0].sceneId, 'scene_four');
  // full = "SSS：\n" + 65 A's = (3 + 2) + 65 = 70
  assert.strictEqual(displayViolations[0].length, 70);
});

if (process.exitCode) {
  console.error('\nSome tests failed.');
  process.exit(1);
} else {
  console.log('\nAll scan_text_budget.js orchestration tests passed.');
}
