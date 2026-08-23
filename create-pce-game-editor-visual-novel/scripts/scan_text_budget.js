#!/usr/bin/env node
'use strict';

/**
 * Scan an emitted PCE scene document (pce-vn-scenes.json shape) for the two
 * build-blocking text constraints documented in
 * references/text-and-font-limits.md:
 *
 *   1. Font coverage: the System Card jp-v3 font only covers JIS Level 1
 *      kanji plus kana/symbols. Level 2 kanji fail the real build one
 *      character at a time. This scans every unique character up front.
 *   2. Display budget: the real per-message display budget is 68 glyph
 *      entries (17 chars x 4 lines), computed from
 *      `speakerDisplayName + '：\n' + text` for a named speaker (zero
 *      prefix cost for narrator), not the looser 96-char raw-storage cap.
 *
 * This script never re-derives the encoding logic itself -- it always calls
 * the live checkout's own `pce-system-card-font.js` exports, so it can never
 * silently drift from the real engine behavior. See
 * references/text-and-font-limits.md for the full rationale.
 *
 * Usage:
 *   node scan_text_budget.js --checkout <path> --scenes <pce-vn-scenes.json>
 *     [--font-module <path>] [--max-display 68] [--report <out.json>]
 */

const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = { maxDisplay: 68 };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--help' || token === '-h') {
      args.help = true;
      continue;
    }
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[i + 1];
    if (key === 'checkout') { args.checkout = value; i += 1; }
    else if (key === 'scenes') { args.scenes = value; i += 1; }
    else if (key === 'font-module') { args.fontModule = value; i += 1; }
    else if (key === 'max-display') { args.maxDisplay = Number(value); i += 1; }
    else if (key === 'report') { args.report = value; i += 1; }
  }
  return args;
}

function printHelp() {
  console.log([
    'scan_text_budget.js — font coverage + display budget scanner',
    '',
    'Required:',
    '  --checkout <path>       Root of the PCE Game Editor checkout (never guessed).',
    '  --scenes <path>         Emitted pce-vn-scenes.json-shaped document to scan.',
    '',
    'Optional:',
    '  --font-module <path>    Explicit path to pce-system-card-font.js.',
    '                          Default: shallow search under --checkout.',
    '  --max-display <n>       Display-budget glyph-entry cap. Default: 68.',
    '  --report <path>         Write the full JSON report to this path.',
  ].join('\n'));
}

function findFontModule(checkoutRoot) {
  const direct = path.join(checkoutRoot, 'pce-system-card-font.js');
  if (fs.existsSync(direct)) return direct;
  const candidates = [];
  const skipDirs = new Set(['node_modules', '.git', 'dist', 'out']);
  (function walk(dir, depth) {
    if (depth > 3) return;
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch (err) {
      return;
    }
    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (skipDirs.has(entry.name)) continue;
        walk(full, depth + 1);
      } else if (entry.name === 'pce-system-card-font.js') {
        candidates.push(full);
      }
    }
  })(checkoutRoot, 0);
  if (candidates.length === 0) return null;
  return candidates[0];
}

function loadFontModule(modulePath) {
  if (!modulePath || !fs.existsSync(modulePath)) {
    throw new Error(
      `pce-system-card-font.js not found (looked at: ${modulePath || '(none)'}). ` +
      'Pass --font-module explicitly or confirm --checkout points at a real checkout.'
    );
  }
  // eslint-disable-next-line import/no-dynamic-require, global-require
  const mod = require(path.resolve(modulePath));
  for (const name of ['normalizeSystemCardText', 'isJapaneseV3GlyphBytes', 'encodeSystemCardText']) {
    if (typeof mod[name] !== 'function') {
      throw new Error(`${modulePath} does not export required function "${name}". This checkout may have renamed the font module's API — update this script or pass a compatible --font-module.`);
    }
  }
  return mod;
}

function loadIconv(checkoutRoot) {
  const candidate = path.join(checkoutRoot, 'node_modules', 'iconv-lite');
  try {
    // eslint-disable-next-line import/no-dynamic-require, global-require
    return require(candidate);
  } catch (err) {
    throw new Error(
      `iconv-lite not found under ${candidate}. It is expected as a transitive dependency of the checkout; ` +
      `if the checkout no longer ships it, adapt the Shift_JIS encoding step in this script. Original error: ${err.message}`
    );
  }
}

/**
 * display.full formula, matching the live engine:
 *   named speaker: displayName + '：\n' + text  (prefix costs len(displayName) + 2 entries)
 *   empty/narrator speaker: text (zero prefix cost)
 */
function displayFull(speaker, text) {
  const trimmedSpeaker = String(speaker || '').trim();
  if (!trimmedSpeaker || trimmedSpeaker.toLowerCase() === 'narrator') return String(text || '');
  return `${trimmedSpeaker}：\n${String(text || '')}`;
}

function collectUniqueChars(strings) {
  const set = new Set();
  for (const str of strings) {
    if (!str) continue;
    for (const ch of String(str)) {
      // Skip ASCII — the font-coverage question only matters for non-ASCII glyphs.
      if (ch.codePointAt(0) > 0x7f) set.add(ch);
    }
  }
  return set;
}

/**
 * Pure, testable core. Takes an already-loaded font module + iconv module so
 * tests can inject stubs instead of the real checkout.
 */
function scanScenes(document, { fontModule, iconv, maxDisplay = 68 } = {}) {
  const fontViolations = [];
  const displayViolations = [];
  const charLocations = new Map(); // char -> [{sceneId, commandIndex, source}]

  const scenes = Array.isArray(document && document.scenes) ? document.scenes : [];

  for (const scene of scenes) {
    const sceneId = scene && scene.id;
    const commands = Array.isArray(scene && scene.commands) ? scene.commands : [];
    commands.forEach((command, commandIndex) => {
      if (!command || typeof command !== 'object') return;

      if (command.type === 'message') {
        const full = displayFull(command.speaker, command.text);
        for (const ch of collectUniqueChars([full])) {
          if (!charLocations.has(ch)) charLocations.set(ch, []);
          const locs = charLocations.get(ch);
          if (locs.length < 5) locs.push({ sceneId, commandIndex, source: 'message' });
        }
        const encoded = fontModule.encodeSystemCardText(full, { sceneId, commandIndex, field: 'message' }, { maxCharacters: 9999 });
        const length = encoded && typeof encoded.length === 'number' ? encoded.length : 0;
        if (length > maxDisplay) {
          displayViolations.push({
            sceneId,
            commandIndex,
            length,
            maxDisplay,
            speaker: command.speaker || '',
            textPreview: String(command.text || '').slice(0, 40),
          });
        }
      } else if (command.type === 'choice' && Array.isArray(command.choices)) {
        command.choices.forEach((choiceOption) => {
          for (const ch of collectUniqueChars([choiceOption && choiceOption.label])) {
            if (!charLocations.has(ch)) charLocations.set(ch, []);
            const locs = charLocations.get(ch);
            if (locs.length < 5) locs.push({ sceneId, commandIndex, source: 'choice.label' });
          }
        });
      } else if (command.type === 'spritetext') {
        for (const ch of collectUniqueChars([command.text])) {
          if (!charLocations.has(ch)) charLocations.set(ch, []);
          const locs = charLocations.get(ch);
          if (locs.length < 5) locs.push({ sceneId, commandIndex, source: 'spritetext' });
        }
      }
    });
  }

  for (const [ch, locations] of charLocations.entries()) {
    let normalized;
    try {
      normalized = fontModule.normalizeSystemCardText(ch);
    } catch (err) {
      fontViolations.push({ char: ch, codepoint: `U+${ch.codePointAt(0).toString(16).toUpperCase()}`, reason: `normalize failed: ${err.message}`, locations });
      continue;
    }
    let ok = false;
    let sjisHex = 'N/A';
    for (const nch of normalized) {
      let buf;
      try {
        buf = iconv.encode(nch, 'Shift_JIS');
      } catch (err) {
        buf = null;
      }
      if (buf && buf.length) {
        sjisHex = buf.toString('hex');
        if (fontModule.isJapaneseV3GlyphBytes(buf)) { ok = true; break; }
      }
    }
    if (!ok) {
      fontViolations.push({ char: ch, codepoint: `U+${ch.codePointAt(0).toString(16).toUpperCase()}`, sjisHex, locations });
    }
  }

  return { fontViolations, displayViolations };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { printHelp(); process.exit(0); }
  if (!args.checkout) { console.error('ERROR: --checkout is required (never guessed).'); process.exit(2); }
  if (!args.scenes) { console.error('ERROR: --scenes is required.'); process.exit(2); }

  const checkoutRoot = path.resolve(args.checkout);
  const scenesPath = path.resolve(args.scenes);
  if (!fs.existsSync(checkoutRoot)) { console.error(`ERROR: --checkout path does not exist: ${checkoutRoot}`); process.exit(2); }
  if (!fs.existsSync(scenesPath)) { console.error(`ERROR: --scenes path does not exist: ${scenesPath}`); process.exit(2); }

  let document;
  try {
    document = JSON.parse(fs.readFileSync(scenesPath, 'utf8'));
  } catch (err) {
    console.error(`ERROR: failed to parse --scenes as JSON: ${err.message}`);
    process.exit(2);
  }

  const fontModulePath = args.fontModule ? path.resolve(args.fontModule) : findFontModule(checkoutRoot);
  let fontModule;
  let iconv;
  try {
    fontModule = loadFontModule(fontModulePath);
    iconv = loadIconv(checkoutRoot);
  } catch (err) {
    console.error(`ERROR: ${err.message}`);
    process.exit(2);
  }

  const { fontViolations, displayViolations } = scanScenes(document, { fontModule, iconv, maxDisplay: args.maxDisplay });

  console.log(`Font coverage violations: ${fontViolations.length}`);
  for (const v of fontViolations) {
    console.log(`  ${v.char} (${v.codepoint}) — ${v.locations.map((l) => `${l.sceneId}:${l.commandIndex}[${l.source}]`).join(', ')}`);
  }
  console.log(`Display budget violations (> ${args.maxDisplay}): ${displayViolations.length}`);
  for (const v of displayViolations) {
    console.log(`  ${v.sceneId}:${v.commandIndex} length=${v.length} speaker="${v.speaker}" text="${v.textPreview}..."`);
  }

  if (args.report) {
    fs.writeFileSync(path.resolve(args.report), JSON.stringify({ fontViolations, displayViolations }, null, 2) + '\n', 'utf8');
    console.log(`Report written to ${path.resolve(args.report)}`);
  }

  process.exit(fontViolations.length > 0 || displayViolations.length > 0 ? 1 : 0);
}

module.exports = { scanScenes, displayFull, collectUniqueChars, findFontModule };

if (require.main === module) {
  main();
}
