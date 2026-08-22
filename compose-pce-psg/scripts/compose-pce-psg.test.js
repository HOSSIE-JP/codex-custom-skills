'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const composer = require('./compose-pce-psg.js');
const scoreLib = require('./pce-score.js');
const migrator = require('./migrate-pce-psg-score.js');
const verifier = require('./verify-pce-psg-artifacts.js');

function passes(status = 'complete') {
  return {
    formMotif: { status, notes: 'reviewed' },
    melodyHarmony: { status, notes: 'reviewed' },
    rhythmArrangement: { status, notes: 'reviewed' },
    loopFatigue: { status, notes: 'reviewed' },
  };
}

function tonalScore(overrides = {}) {
  const score = {
    schemaVersion: 2,
    id: 'natural_loop',
    name: 'Natural Loop',
    type: 'psg-song',
    loop: true,
    intent: {
      purpose: 'Quiet visual novel conversation BGM',
      emotion: ['warm', 'curious'],
      sceneFunction: 'Support dialogue without masking it',
      energyCurve: ['A:low', 'B:medium'],
      tensionCurve: ['A:stable', 'B:return'],
      hardwareTargets: ['both'],
    },
    styleProfile: 'tonal',
    transport: {
      bpm: 108,
      timeSignature: '4/4',
      resolution: 4,
      bars: 4,
      speed: 6,
      loop: { enabled: true, startStep: 0, endStep: 64, intentionalDiscontinuity: false },
    },
    tonality: { tonic: 'C', mode: 'major', scale: ['C', 'D', 'E', 'F', 'G', 'A', 'B'] },
    form: [
      { id: 'A', name: 'A', startBar: 1, endBar: 2, function: 'stable opening', energy: 0.25, tension: 0.2 },
      { id: 'B', name: 'B', startBar: 3, endBar: 4, function: 'gentle answer', energy: 0.45, tension: 0.35 },
    ],
    harmony: [
      { step: 0, duration: 16, symbol: 'C', function: 'T', pitches: ['C3', 'E3', 'G3'] },
      { step: 16, duration: 16, symbol: 'F', function: 'S', pitches: ['F3', 'A3', 'C4'] },
      { step: 32, duration: 16, symbol: 'G', function: 'D', pitches: ['G3', 'B3', 'D4'] },
      { step: 48, duration: 16, symbol: 'C', function: 'T', pitches: ['C3', 'E3', 'G3'] },
    ],
    motifs: [{ id: 'answer', intervals: [0, 2, 4], rhythm: [1, 1, 2], description: 'rising answer' }],
    parts: [
      {
        id: 'melody', role: 'melody', channel: 0, range: { min: 'C4', max: 'C6' }, wave: 45, volume: 18,
        events: [
          { step: 0, duration: 4, note: 'C4', volume: 18, wave: 45, articulation: 'normal' },
          { step: 8, duration: 4, note: 'E4', volume: 17, wave: 45, articulation: 'normal' },
          { step: 16, duration: 4, note: 'F4', volume: 18, wave: 45, articulation: 'normal' },
          { step: 24, duration: 4, note: 'A4', volume: 17, wave: 45, articulation: 'normal' },
          { step: 32, duration: 4, note: 'G4', volume: 19, wave: 45, articulation: 'normal' },
          { step: 40, duration: 4, note: 'D5', volume: 17, wave: 45, articulation: 'normal' },
          { step: 48, duration: 4, note: 'E5', volume: 18, wave: 45, articulation: 'normal' },
          { step: 56, duration: 4, note: 'C5', volume: 16, wave: 45, articulation: 'normal' },
        ],
      },
      {
        id: 'bass', role: 'bass', channel: 1, range: { min: 'C2', max: 'C4' }, wave: 20, volume: 12,
        events: [
          { step: 0, duration: 16, note: 'C3', articulation: 'normal' },
          { step: 16, duration: 16, note: 'F3', articulation: 'normal' },
          { step: 32, duration: 16, note: 'G3', articulation: 'normal' },
          { step: 48, duration: 16, note: 'C3', articulation: 'normal' },
        ],
      },
      {
        id: 'percussion', role: 'percussion', channel: 4, noise: true, volume: 6,
        events: [0, 8, 16, 24, 32, 36, 40, 48, 52, 56].map((step) => ({ step, duration: 1, noisePeriod: 7, articulation: 'staccato' })),
      },
    ],
    mix: { channels: 5, masterVolume: 90, defaultWave: 45, fallbackPeriod: 428, densityTarget: 'dialogue-light' },
    review: { audition: 'complete', notes: ['Read through at loop seam.'], passes: passes(), waivedFindingIds: [] },
  };
  return { ...score, ...overrides };
}

function v1Score(overrides = {}) {
  return {
    schemaVersion: 1,
    id: 'legacy_song',
    name: 'Legacy Song',
    type: 'psg-song',
    loop: true,
    bpm: 120,
    steps: 64,
    channels: 6,
    speed: 6,
    period: 428,
    wave: 45,
    masterVolume: 100,
    timeSignature: '4/4',
    stepsPerBar: 16,
    sections: [{ name: 'A', startBar: 1, endBar: 4, startStep: 0 }],
    events: [
      { step: 0, channel: 0, period: 428, volume: 18, wave: 45, note: 'C4' },
      { step: 3, channel: 0, period: 428, volume: 0, wave: 45 },
      { step: 8, channel: 4, period: 7, volume: 6, noise: true },
    ],
    ...overrides,
  };
}

test('v2 generation is canonical and embeds authoring hash', () => {
  const score = tonalScore();
  const first = composer.renderDocument(score);
  const second = composer.renderDocument(JSON.parse(JSON.stringify(score)));
  assert.equal(first, second);
  const document = JSON.parse(first);
  assert.equal(document.version, 2);
  assert.equal(document.assets.length, 1);
  assert.equal(document.assets[0].options.steps, 64);
  assert.equal(document.authoring.scoreSchemaVersion, 2);
  assert.match(document.authoring.scoreSha256, /^[0-9a-f]{64}$/);
});

test('note names, enharmonic names, and PCE period calculation agree', () => {
  assert.equal(composer.noteNameToMidi('C4'), 60);
  assert.equal(composer.noteNameToMidi('B#3'), 60);
  assert.equal(composer.noteNameToMidi('Db4'), 61);
  assert.equal(composer.midiNoteToPeriod(69), Math.round(3579545 / (32 * 440)));
  assert.equal(composer.midiNoteToPeriod(60), composer.generateDocument(tonalScore()).assets[0].options.pattern[0].period);
});

test('note and explicit period mismatch is rejected', () => {
  const score = tonalScore();
  score.parts[0].events[0].period = 999;
  assert.throws(() => composer.generateDocument(score), /does not match calculated period/);
});

test('unsupported low pitch and part range violations are rejected', () => {
  const low = tonalScore();
  low.parts[0].range.min = 'C0';
  low.parts[0].events[0].note = 'C0';
  assert.throws(() => composer.generateDocument(low), /outside PCE period range/);
  const range = tonalScore();
  range.parts[0].events[0].note = 'C3';
  assert.throws(() => composer.generateDocument(range), /outside part range/);
});

test('duration emits a note-off and same-step reattack wins', () => {
  const score = tonalScore();
  score.parts = [{
    id: 'melody', role: 'melody', channel: 0, range: { min: 'A#3', max: 'C6' }, wave: 45, volume: 18,
    events: [
      { step: 0, duration: 4, note: 'C4', articulation: 'legato' },
      { step: 4, duration: 4, note: 'D4', articulation: 'staccato' },
    ],
  }];
  score.mix.channels = 1;
  const pattern = composer.generateDocument(score).assets[0].options.pattern;
  assert.deepEqual(pattern.map((event) => [event.step, event.volume]), [[0, 18], [4, 18], [6, 0]]);
});

test('motif transforms expand deterministically and retain source score', () => {
  const score = tonalScore();
  score.parts = [{
    id: 'melody', role: 'melody', channel: 0, range: { min: 'A#3', max: 'C6' }, wave: 45, volume: 18,
    events: [{
      step: 0, duration: 4, note: 'C5', motifRef: 'answer', articulation: 'legato',
      transform: { transpose: 2, octave: -1, inversion: true, rhythmScale: 1, fragmentStart: 0, fragmentLength: 3 },
    }],
  }];
  score.mix.channels = 1;
  const artifacts = composer.generateArtifacts(score);
  const onsets = artifacts.compiled.expanded.pattern.filter((event) => event.volume > 0);
  assert.deepEqual(onsets.map((event) => [event.step, event.note]), [[0, 'D4'], [1, 'C4'], [2, 'A#3']]);
  assert.equal(JSON.parse(artifacts.scoreText).parts[0].events[0].motifRef, 'answer');
});

test('overlapping parts on one channel are rejected without voice stealing', () => {
  const score = tonalScore();
  score.parts.push({
    id: 'counter', role: 'countermelody', channel: 0, range: { min: 'C4', max: 'C6' }, wave: 22, volume: 12,
    events: [{ step: 2, duration: 4, note: 'G4', articulation: 'normal' }],
  });
  assert.throws(() => composer.generateDocument(score), /channel 0 overlap/);
});

test('noise is limited to channels 4 and 5', () => {
  const score = tonalScore();
  score.parts[2].channel = 3;
  assert.throws(() => composer.generateDocument(score), /channel 4 or 5/);
});

test('CLI writes four deterministic standard artifacts and verifier accepts them', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'compose-pce-psg-'));
  const scorePath = path.join(directory, 'input.json');
  const output = path.join(directory, 'out');
  fs.writeFileSync(scorePath, JSON.stringify(tonalScore({ id: 'cli_song' })));
  const files = composer.main(['--score', scorePath, '--out', output]);
  assert.deepEqual(fs.readdirSync(output), ['cli_song.audit.json', 'cli_song.audit.md', 'cli_song.psg.json', 'cli_song.score.json']);
  const first = fs.readFileSync(files.psg);
  composer.main(['--score', scorePath, '--out', output]);
  assert.deepEqual(first, fs.readFileSync(files.psg));
  assert.equal(verifier.main(['--audit', files.audit]).psgPath, files.psg);
});

test('verifier rejects a stale PSG and stale audit Markdown', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'compose-pce-stale-'));
  const input = path.join(directory, 'input.json');
  fs.writeFileSync(input, JSON.stringify(tonalScore({ id: 'stale_song' })));
  const files = composer.main(['--score', input, '--out', directory]);
  fs.appendFileSync(files.psg, ' ');
  assert.throws(() => verifier.main(['--audit', files.audit]), /stale PSG/);
  const fresh = composer.main(['--score', input, '--out', directory]);
  fs.writeFileSync(fresh.auditMarkdown, '# stale\n');
  assert.throws(() => verifier.main(['--audit', fresh.audit]), /stale audit Markdown/);
});

test('v1 migration preserves byte-identical PSG and does not infer intent', () => {
  const legacy = v1Score();
  const migrated = composer.migrateV1Score(legacy);
  const golden = {
    version: 2,
    assets: [{
      id: 'legacy_song',
      type: 'psg-song',
      name: 'Legacy Song',
      source: '',
      options: {
        kind: 'song',
        bpm: 120,
        speed: 6,
        period: 428,
        wave: 45,
        channels: 6,
        steps: 64,
        volume: 100,
        loop: true,
        timeSignature: '4/4',
        bars: 4,
        stepsPerBar: 16,
        sections: [{ name: 'A', startBar: 1, endBar: 4, startStep: 0 }],
        pattern: [
          { step: 0, channel: 0, period: 428, volume: 18, note: 'C4', wave: 45 },
          { step: 3, channel: 0, period: 428, volume: 0, wave: 45 },
          { step: 8, channel: 4, period: 7, volume: 6, noise: 1 },
        ],
      },
    }],
  };
  assert.equal(composer.renderDocument(legacy), `${JSON.stringify(golden, null, 2)}\n`);
  assert.equal(composer.renderDocument(legacy), composer.renderDocument(migrated));
  assert.equal(migrated.styleProfile, null);
  assert.equal(migrated.tonality, null);
  assert.deepEqual(migrated.motifs, []);
  assert.ok(migrated.parts.every((part) => part.legacyExact));
});

test('migration CLI writes a reusable normalized schema version 2 score', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'compose-pce-migrate-'));
  const sourcePath = path.join(directory, 'legacy.json');
  fs.writeFileSync(sourcePath, JSON.stringify(v1Score()));
  const outputPath = migrator.main(['--score', sourcePath, '--out', directory]);
  const migrated = JSON.parse(fs.readFileSync(outputPath, 'utf8'));
  assert.equal(migrated.schemaVersion, 2);
  assert.equal(migrated.migration.exact, true);
  assert.equal(composer.renderDocument(v1Score()), composer.renderDocument(migrated));
});

test('profile lenses preserve modal, ambient, action, and SFX counterexamples', () => {
  const modal = tonalScore({ styleProfile: 'modal' });
  modal.tonality.mode = 'dorian';
  const modalAudit = composer.generateArtifacts(modal).audit;
  assert.equal(modalAudit.findings.some((entry) => entry.ruleId === 'tonal-strong-beat-instability'), false);

  const ambient = tonalScore({ styleProfile: 'ambient' });
  ambient.parts = [ambient.parts[0]];
  ambient.parts[0].events = [ambient.parts[0].events[0]];
  ambient.mix.channels = 1;
  const ambientAudit = composer.generateArtifacts(ambient).audit;
  assert.equal(ambientAudit.findings.some((entry) => entry.ruleId === 'profile-density-low'), false);

  const action = tonalScore({ styleProfile: 'action' });
  action.parts = [action.parts[0]];
  action.parts[0].events = [0, 16, 32, 48].map((step) => ({ step, duration: 4, note: 'C4', articulation: 'staccato' }));
  action.mix.channels = 1;
  const repetition = composer.generateArtifacts(action).audit.findings.find((entry) => entry.ruleId === 'repetition-exact-all-bars');
  assert.equal(repetition.severity, 'information');

  const sfx = tonalScore({ type: 'psg-sfx', loop: false, styleProfile: 'sfx-jingle' });
  sfx.transport.loop = { enabled: false, startStep: 0, endStep: 64, intentionalDiscontinuity: false };
  assert.equal(composer.generateDocument(sfx).assets[0].options.kind, 'sfx');
});

test('range boundary and declared energy contrast do not trigger masking/contrast warnings', () => {
  const audit = composer.generateArtifacts(tonalScore()).audit;
  assert.equal(audit.findings.some((entry) => entry.ruleId === 'arrangement-range-overlap'), false);
  assert.equal(audit.findings.some((entry) => entry.ruleId === 'section-contrast-low'), false);
});

test('tonal strong-beat instability and loop seam are profile warnings', () => {
  const score = tonalScore();
  score.parts[0].range.max = 'D6';
  score.parts[0].events.forEach((event) => { event.note = 'C#4'; });
  score.parts[0].events[score.parts[0].events.length - 1] = { step: 60, duration: 4, note: 'C#6', articulation: 'legato' };
  const audit = composer.generateArtifacts(score).audit;
  assert.ok(audit.findings.some((entry) => entry.ruleId === 'tonal-strong-beat-instability'));
  const seam = audit.findings.find((entry) => entry.ruleId === 'loop-pitch-seam');
  assert.equal(seam.severity, 'profile-warning');
  score.transport.loop.intentionalDiscontinuity = true;
  const intentional = composer.generateArtifacts(score).audit.findings.find((entry) => entry.ruleId === 'loop-pitch-seam');
  assert.equal(intentional.severity, 'information');
});

test('audit records real eight-byte PCE serialization budget and remains deterministic', () => {
  const first = composer.generateArtifacts(tonalScore());
  const second = composer.generateArtifacts(JSON.parse(first.scoreText));
  assert.equal(first.auditText, second.auditText);
  assert.equal(first.audit.metrics.serializedPatternBytes, first.audit.metrics.patternEvents * 8);
  assert.equal(first.audit.status.technical, 'pass');
  assert.equal(typeof first.audit.metrics.onsetLockRatio, 'number');
  assert.equal(first.audit.metrics.targetMedia.hucard.periodRangeValid, true);
});

test('target-media audit reports System Card period approximation when requested', () => {
  const migrated = composer.migrateV1Score(v1Score({
    events: [{ step: 0, channel: 0, period: 4095, volume: 18, wave: 45 }],
  }));
  migrated.intent.hardwareTargets = ['both'];
  const audit = composer.generateArtifacts(migrated).audit;
  assert.ok(audit.metrics.targetMedia.cdrom2SystemCard.approximationCount > 0);
  assert.ok(audit.findings.some((entry) => entry.ruleId === 'target-period-approximation'));
});

test('expanded motif scale departures identify pitch classes and occurrences', () => {
  const score = tonalScore();
  score.parts[0].events[0].note = 'C#4';
  score.parts[0].events[1].note = 'D#4';
  const finding = composer.generateArtifacts(score).audit.findings.find((entry) => entry.ruleId === 'expanded-pitch-outside-scale');
  assert.equal(finding.severity, 'profile-warning');
  assert.ok(finding.details.pitchClasses.includes('C#'));
  assert.ok(finding.details.occurrences.some((entry) => entry.partId === 'melody'));
});

test('short onset-locked action loop emits fatigue information without imposing tonal rules', () => {
  const score = tonalScore({ styleProfile: 'action' });
  score.transport.bpm = 300;
  score.parts = [
    {
      id: 'pulse', role: 'bass', channel: 0, range: { min: 'C3', max: 'C4' }, wave: 45, volume: 18,
      events: [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60].map((step) => ({ step, duration: 2, note: 'C3', articulation: 'staccato' })),
    },
    {
      id: 'drums', role: 'percussion', channel: 4, noise: true, volume: 8,
      events: [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60].map((step) => ({ step, duration: 1, noisePeriod: 7, articulation: 'staccato' })),
    },
  ];
  score.mix.channels = 5;
  const audit = composer.generateArtifacts(score).audit;
  assert.ok(audit.findings.some((entry) => entry.ruleId === 'action-onset-lock-high' && entry.severity === 'information'));
  assert.ok(audit.findings.some((entry) => entry.ruleId === 'short-loop-fatigue-review' && entry.severity === 'information'));
  assert.equal(audit.findings.some((entry) => entry.ruleId === 'tonal-strong-beat-instability'), false);
});

test('motif validation errors identify part, event, and expanded pitch', () => {
  const score = tonalScore();
  score.parts[0].events = [{
    step: 0, duration: 4, note: 'C6', motifRef: 'answer', articulation: 'legato',
    transform: { transpose: 12, octave: 0, inversion: false, rhythmScale: 1, fragmentStart: 0, fragmentLength: 3 },
  }];
  assert.throws(() => composer.generateArtifacts(score), /outside part melody range at part melody, event 0, step 0/);
});

test('optional preview is RIFF/WAVE and is not a standard artifact', () => {
  const plain = composer.generateArtifacts(tonalScore());
  assert.equal(plain.preview, null);
  const wav = composer.generateArtifacts(tonalScore(), { preview: true }).preview;
  assert.equal(wav.subarray(0, 4).toString('ascii'), 'RIFF');
  assert.equal(wav.subarray(8, 12).toString('ascii'), 'WAVE');
});

test('v1 boundary and event-count validation remains compatible', () => {
  assert.equal(composer.generateDocument(v1Score()).assets[0].type, 'psg-song');
  assert.throws(() => composer.generateDocument(v1Score({ bpm: 29 })), /bpm/);
  assert.throws(() => composer.generateDocument(v1Score({ events: [{ step: 0, channel: 3, period: 1, volume: 1, noise: true }] })), /channel 4 or 5/);
  const events = Array.from({ length: 2049 }, (_, index) => ({ step: index % 64, channel: index % 6, period: 1, volume: 1, wave: 0 }));
  assert.throws(() => composer.generateDocument(v1Score({ events })), /at most 2048/);
});

test('unknown profile, resolution, field, and song loop mismatch are rejected', () => {
  assert.throws(() => composer.generateDocument(tonalScore({ styleProfile: 'classical' })), /styleProfile/);
  const resolution = tonalScore(); resolution.transport.resolution = 3;
  assert.throws(() => composer.generateDocument(resolution), /resolution/);
  const field = tonalScore(); field.typo = true;
  assert.throws(() => composer.generateDocument(field), /unknown field/);
  const loop = tonalScore(); loop.loop = false;
  assert.throws(() => composer.generateDocument(loop), /loop must be true/);
});
