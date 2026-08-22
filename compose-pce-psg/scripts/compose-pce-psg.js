#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const scoreLib = require('./pce-score.js');
const auditLib = require('./pce-audit.js');

function fail(message) { throw new Error(message); }

function renderDocument(rawScore) {
  return scoreLib.canonical(scoreLib.compileScore(rawScore).document);
}

function generateDocument(rawScore) {
  return scoreLib.compileScore(rawScore).document;
}

function generateArtifacts(rawScore, options = {}) {
  const compiled = scoreLib.compileScore(rawScore);
  const psgText = scoreLib.canonical(compiled.document);
  const audit = auditLib.build(compiled, psgText);
  const auditText = scoreLib.canonical(audit);
  return {
    compiled,
    scoreText: compiled.scoreText,
    psgText,
    audit,
    auditText,
    auditMarkdown: auditLib.markdown(audit, scoreLib.sha256(auditText)),
    preview: options.preview ? renderPreviewWav(compiled) : null,
  };
}

function renderPreviewWav(compiled, maxSeconds = 180) {
  const sampleRate = 22050;
  const duration = (compiled.score.transport.steps * 15) / compiled.score.transport.bpm;
  if (duration > maxSeconds) fail(`preview duration ${duration.toFixed(3)} seconds exceeds ${maxSeconds}-second safety limit`);
  const frames = Math.max(1, Math.ceil(duration * sampleRate));
  const pcm = Buffer.alloc(frames * 2);
  const states = Array.from({ length: 6 }, () => ({ period: 512, volume: 0, wave: 45, noise: false, phase: 0, lfsr: 0x1ace }));
  const byStep = new Map();
  compiled.expanded.pattern.forEach((event) => {
    if (!byStep.has(event.step)) byStep.set(event.step, []);
    byStep.get(event.step).push(event);
  });
  const samplesPerStep = (15 / compiled.score.transport.bpm) * sampleRate;
  let previousStep = -1;
  for (let frame = 0; frame < frames; frame += 1) {
    const step = Math.min(compiled.score.transport.steps - 1, Math.floor(frame / samplesPerStep));
    if (step !== previousStep) {
      for (let current = previousStep + 1; current <= step; current += 1) {
        (byStep.get(current) || []).forEach((event) => {
          Object.assign(states[event.channel], {
            period: event.period,
            volume: event.volume,
            wave: event.wave == null ? 45 : event.wave,
            noise: event.noise,
          });
        });
      }
      previousStep = step;
    }
    let mixed = 0;
    states.forEach((state) => {
      if (!state.volume) return;
      let oscillator;
      if (state.noise) {
        const bit = ((state.lfsr >> 0) ^ (state.lfsr >> 2) ^ (state.lfsr >> 3) ^ (state.lfsr >> 5)) & 1;
        state.lfsr = (state.lfsr >> 1) | (bit << 15);
        oscillator = state.lfsr & 1 ? 1 : -1;
      } else {
        const frequency = scoreLib.PSG_CLOCK / (32 * state.period);
        state.phase = (state.phase + frequency / sampleRate) % 1;
        const family = state.wave === 45 ? 0 : state.wave % 4;
        oscillator = family === 0 ? (state.phase < 0.5 ? 1 : -1)
          : family === 1 ? Math.sin(state.phase * Math.PI * 2)
            : family === 2 ? (2 * state.phase) - 1
              : 1 - (4 * Math.abs(state.phase - 0.5));
      }
      mixed += oscillator * (state.volume / 31);
    });
    pcm.writeInt16LE(Math.round(Math.max(-1, Math.min(1, mixed / 6)) * 30000), frame * 2);
  }
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + pcm.length, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(1, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write('data', 36);
  header.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([header, pcm]);
}

function parseArguments(argv) {
  const result = { preview: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--preview') {
      if (result.preview) fail('--preview may be specified only once');
      result.preview = true;
      continue;
    }
    if (arg !== '--score' && arg !== '--out') fail(`unknown argument: ${arg}`);
    if (index + 1 >= argv.length || argv[index + 1].startsWith('--')) fail(`${arg} requires a value`);
    const key = arg.slice(2);
    if (result[key] != null) fail(`${arg} may be specified only once`);
    result[key] = argv[index + 1];
    index += 1;
  }
  if (!result.score) fail('--score is required');
  if (!result.out) fail('--out is required');
  return result;
}

function readJson(filePath, label) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    fail(`could not read ${label} JSON ${filePath}: ${error.message}`);
  }
}

function main(argv = process.argv.slice(2)) {
  const args = parseArguments(argv);
  const rawScore = readJson(path.resolve(args.score), 'score');
  const artifacts = generateArtifacts(rawScore, { preview: args.preview });
  const outputDirectory = path.resolve(args.out);
  fs.mkdirSync(outputDirectory, { recursive: true });
  const id = artifacts.compiled.score.id;
  const files = {
    score: path.join(outputDirectory, `${id}.score.json`),
    psg: path.join(outputDirectory, `${id}.psg.json`),
    audit: path.join(outputDirectory, `${id}.audit.json`),
    auditMarkdown: path.join(outputDirectory, `${id}.audit.md`),
  };
  fs.writeFileSync(files.score, artifacts.scoreText, 'utf8');
  fs.writeFileSync(files.psg, artifacts.psgText, 'utf8');
  fs.writeFileSync(files.audit, artifacts.auditText, 'utf8');
  fs.writeFileSync(files.auditMarkdown, artifacts.auditMarkdown, 'utf8');
  if (artifacts.preview) {
    files.preview = path.join(outputDirectory, `${id}.preview.wav`);
    fs.writeFileSync(files.preview, artifacts.preview);
  }
  Object.values(files).forEach((filePath) => process.stdout.write(`${filePath}\n`));
  return files;
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`compose-pce-psg: ${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = {
  generateArtifacts,
  generateDocument,
  main,
  midiNoteToPeriod: scoreLib.midiNoteToPeriod,
  migrateV1Score(rawScore) {
    return scoreLib.compileScore(rawScore).publicScore;
  },
  noteNameToMidi: scoreLib.noteNameToMidi,
  parseArguments,
  renderDocument,
  renderPreviewWav,
  validateScore(rawScore) {
    return rawScore.schemaVersion === 1 ? scoreLib.validateV1(rawScore) : scoreLib.validateV2(rawScore);
  },
};
