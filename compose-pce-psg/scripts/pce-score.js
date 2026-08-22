'use strict';

const crypto = require('node:crypto');

const GENERATOR_VERSION = 2;
const PSG_CLOCK = 3579545;
const MAX_STEPS = 4096;
const MAX_EVENTS = 2048;
const STYLE_PROFILES = new Set(['tonal', 'modal', 'ambient', 'action', 'sfx-jingle']);
const REVIEW_PASSES = ['formMotif', 'melodyHarmony', 'rhythmArrangement', 'loopFatigue'];
const NOTE_BASES = Object.freeze({ C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 });
const ARTICULATIONS = new Set(['normal', 'legato', 'staccato', 'tenuto']);

function fail(message) { throw new Error(message); }
function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${label} must be an object`);
  return value;
}
function fields(value, allowed, label) {
  const unknown = Object.keys(value).filter((key) => !allowed.includes(key));
  if (unknown.length) fail(`${label} contains unknown field(s): ${unknown.join(', ')}`);
}
function integer(value, min, max, label) {
  if (!Number.isInteger(value) || value < min || value > max) fail(`${label} must be an integer from ${min} to ${max}`);
  return value;
}
function numberValue(value, min, max, label) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) fail(`${label} must be a number from ${min} to ${max}`);
  return value;
}
function text(value, label, max = Infinity) {
  if (typeof value !== 'string' || !value.trim() || value.length > max) fail(`${label} must be a non-empty string${Number.isFinite(max) ? ` with at most ${max} characters` : ''}`);
  return value;
}
function id(value, label = 'id') {
  const result = text(value, label, 48);
  if (!/^[A-Za-z0-9_-]+$/.test(result)) fail(`${label} must use only letters, numbers, _ or -`);
  return result;
}
function strings(value, label, max = 64) {
  if (!Array.isArray(value) || value.length > max) fail(`${label} must be an array with at most ${max} entries`);
  return value.map((entry, index) => text(entry, `${label}[${index}]`, 256));
}
function optionalString(value, fallback, label, max) {
  if (value == null) return fallback;
  if (typeof value !== 'string' || value.length > max) fail(`${label} must be a string with at most ${max} characters`);
  return value;
}
function canonical(value) { return `${JSON.stringify(value, null, 2)}\n`; }
function sha256(value) { return crypto.createHash('sha256').update(value).digest('hex'); }

function noteNameToMidi(value, label = 'note') {
  const note = text(value, label, 8);
  const match = /^([A-Ga-g])([#b]{0,2})(-1|[0-9])$/.exec(note);
  if (!match) fail(`${label} must be a note such as C4, F#3, Bb2, or C-1`);
  let pitch = NOTE_BASES[match[1].toUpperCase()];
  for (const accidental of match[2]) pitch += accidental === '#' ? 1 : -1;
  const midi = ((Number(match[3]) + 1) * 12) + pitch;
  if (midi < 0 || midi > 127) fail(`${label} resolves outside MIDI note range 0..127`);
  return midi;
}
function midiToNoteName(midi) {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  return `${names[midi % 12]}${Math.floor(midi / 12) - 1}`;
}
function midiNoteToPeriod(midi) {
  integer(midi, 0, 127, 'midi');
  const frequency = 440 * Math.pow(2, (midi - 69) / 12);
  const period = Math.round(PSG_CLOCK / (32 * frequency));
  if (period < 1 || period > 4095) fail(`MIDI note ${midi} (${midiToNoteName(midi)}) is outside PCE period range 1..4095`);
  return period;
}
function signature(value, label = 'timeSignature') {
  const match = /^(\d+)\/(\d+)$/.exec(text(value, label, 16));
  if (!match) fail(`${label} must use number/number form`);
  const numerator = integer(Number(match[1]), 1, 32, `${label} numerator`);
  const denominator = integer(Number(match[2]), 1, 32, `${label} denominator`);
  if ((denominator & (denominator - 1)) !== 0) fail(`${label} denominator must be a power of two`);
  return { text: `${numerator}/${denominator}`, numerator, denominator };
}

const V1_ROOT = ['schemaVersion', 'id', 'name', 'type', 'loop', 'bpm', 'steps', 'channels', 'speed', 'period', 'wave', 'masterVolume', 'timeSignature', 'stepsPerBar', 'sections', 'events'];
function validateV1(raw) {
  const score = object(raw, 'score');
  fields(score, V1_ROOT, 'score');
  if (score.schemaVersion !== 1) fail('schemaVersion must be 1');
  const result = {
    schemaVersion: 1,
    id: id(score.id),
    name: text(score.name, 'name', 128),
    type: score.type,
    loop: score.loop,
    bpm: integer(score.bpm, 30, 300, 'bpm'),
    steps: integer(score.steps, 1, MAX_STEPS, 'steps'),
    channels: integer(score.channels, 1, 6, 'channels'),
    speed: score.speed == null ? 6 : integer(score.speed, 1, 16, 'speed'),
    period: integer(score.period, 1, 4095, 'period'),
    wave: integer(score.wave, 0, 45, 'wave'),
    masterVolume: score.masterVolume == null ? 100 : integer(score.masterVolume, 0, 100, 'masterVolume'),
    timeSignature: score.timeSignature == null ? '4/4' : signature(score.timeSignature).text,
  };
  if (result.type !== 'psg-song' && result.type !== 'psg-sfx') fail('type must be psg-song or psg-sfx');
  if (result.loop !== (result.type === 'psg-song')) fail(`loop must be ${result.type === 'psg-song'} for ${result.type}`);
  result.stepsPerBar = score.stepsPerBar == null ? Math.min(16, result.steps) : integer(score.stepsPerBar, 1, result.steps, 'stepsPerBar');
  const bars = Math.ceil(result.steps / result.stepsPerBar);
  const names = new Set();
  let previousEnd = 0;
  result.sections = (score.sections || []).map((entry, index) => {
    const label = `sections[${index}]`;
    fields(object(entry, label), ['name', 'startBar', 'endBar', 'startStep'], label);
    const section = {
      name: text(entry.name, `${label}.name`, 64),
      startBar: integer(entry.startBar, 1, bars, `${label}.startBar`),
      endBar: integer(entry.endBar, entry.startBar, bars, `${label}.endBar`),
      startStep: integer(entry.startStep, 0, result.steps - 1, `${label}.startStep`),
    };
    if (section.startStep !== (section.startBar - 1) * result.stepsPerBar) fail(`${label}.startStep does not match startBar`);
    if (section.startBar <= previousEnd) fail(`${label} overlaps or is out of order`);
    if (names.has(section.name)) fail(`${label}.name duplicates ${section.name}`);
    names.add(section.name); previousEnd = section.endBar;
    return section;
  });
  if (!Array.isArray(score.events) || score.events.length > MAX_EVENTS) fail(`events must be an array with at most ${MAX_EVENTS} events`);
  const occupied = new Set();
  result.events = score.events.map((entry, index) => {
    const label = `events[${index}]`;
    fields(object(entry, label), ['step', 'channel', 'period', 'volume', 'wave', 'noise', 'note'], label);
    const noise = entry.noise === true;
    const event = {
      step: integer(entry.step, 0, result.steps - 1, `${label}.step`),
      channel: integer(entry.channel, 0, 5, `${label}.channel`),
      period: integer(entry.period, 1, 4095, `${label}.period`),
      volume: integer(entry.volume, 0, 31, `${label}.volume`),
      wave: noise ? null : (entry.wave == null ? result.wave : integer(entry.wave, 0, 45, `${label}.wave`)),
      noise,
      note: entry.note == null ? null : text(entry.note, `${label}.note`, 32),
    };
    if (event.channel >= result.channels) fail(`${label}.channel must be less than channels`);
    if (noise && event.channel < 4) fail(`${label}.noise is only valid on channel 4 or 5`);
    if (noise && entry.wave != null) fail(`${label}.wave must be omitted for a noise event`);
    const key = `${event.step}:${event.channel}`;
    if (occupied.has(key)) fail(`${label} duplicates step ${event.step}, channel ${event.channel}`);
    occupied.add(key);
    return event;
  }).sort((a, b) => a.step - b.step || a.channel - b.channel);
  return result;
}

const ROOT2 = ['schemaVersion', 'id', 'name', 'type', 'loop', 'intent', 'styleProfile', 'transport', 'tonality', 'form', 'harmony', 'motifs', 'parts', 'mix', 'review', 'migration'];
const PART_ROLES = new Set(['melody', 'countermelody', 'harmony', 'arpeggio', 'pad', 'bass', 'percussion', 'accent', 'legacy']);

function normalizeIntent(raw) {
  fields(object(raw, 'intent'), ['purpose', 'emotion', 'sceneFunction', 'energyCurve', 'tensionCurve', 'hardwareTargets'], 'intent');
  const targets = raw.hardwareTargets == null ? ['generic'] : strings(raw.hardwareTargets, 'intent.hardwareTargets', 4);
  const allowed = new Set(['generic', 'cdrom2', 'hucard', 'both']);
  targets.forEach((target) => { if (!allowed.has(target)) fail(`unknown hardware target ${target}`); });
  return {
    purpose: text(raw.purpose, 'intent.purpose', 256),
    emotion: strings(raw.emotion, 'intent.emotion', 16),
    sceneFunction: text(raw.sceneFunction, 'intent.sceneFunction', 256),
    energyCurve: strings(raw.energyCurve, 'intent.energyCurve', 32),
    tensionCurve: strings(raw.tensionCurve, 'intent.tensionCurve', 32),
    hardwareTargets: targets,
  };
}

function normalizeTransport(raw, type, migrated = false) {
  fields(object(raw, 'transport'), ['bpm', 'timeSignature', 'resolution', 'bars', 'speed', 'loop', 'legacySteps', 'legacyStepsPerBar'], 'transport');
  const time = signature(raw.timeSignature, 'transport.timeSignature');
  const resolution = integer(raw.resolution, 4, 4, 'transport.resolution');
  const stepsPerBar = time.numerator * resolution * (4 / time.denominator);
  if (!Number.isInteger(stepsPerBar) || stepsPerBar < 1) fail('time signature cannot be represented on a 16th-note grid');
  const bars = integer(raw.bars, 1, MAX_STEPS, 'transport.bars');
  const resolvedStepsPerBar = migrated && raw.legacyStepsPerBar != null
    ? integer(raw.legacyStepsPerBar, 1, MAX_STEPS, 'transport.legacyStepsPerBar')
    : stepsPerBar;
  const steps = migrated && raw.legacySteps != null
    ? integer(raw.legacySteps, 1, MAX_STEPS, 'transport.legacySteps')
    : bars * resolvedStepsPerBar;
  if (steps > MAX_STEPS) fail(`transport produces ${steps} steps; maximum is ${MAX_STEPS}`);
  const loopRaw = object(raw.loop, 'transport.loop');
  fields(loopRaw, ['enabled', 'startStep', 'endStep', 'intentionalDiscontinuity'], 'transport.loop');
  const enabled = loopRaw.enabled === true;
  if (enabled !== (type === 'psg-song')) fail(`transport.loop.enabled must be ${type === 'psg-song'} for ${type}`);
  const startStep = loopRaw.startStep == null ? 0 : integer(loopRaw.startStep, 0, steps - 1, 'transport.loop.startStep');
  const endStep = loopRaw.endStep == null ? steps : integer(loopRaw.endStep, 1, steps, 'transport.loop.endStep');
  if (startStep !== 0 || endStep !== steps) fail('PCE PSG loop metadata must cover the complete asset');
  return {
    bpm: integer(raw.bpm, 30, 300, 'transport.bpm'),
    timeSignature: time.text,
    resolution,
    bars,
    speed: raw.speed == null ? 6 : integer(raw.speed, 1, 16, 'transport.speed'),
    stepsPerBar: resolvedStepsPerBar,
    steps,
    loop: { enabled, startStep, endStep, intentionalDiscontinuity: loopRaw.intentionalDiscontinuity === true },
  };
}

function normalizeForm(raw, transport, migrated = false) {
  if (!Array.isArray(raw) || (!migrated && !raw.length)) fail('form must be a non-empty array');
  const ids = new Set();
  let previousEnd = 0;
  const result = raw.map((entry, index) => {
    const label = `form[${index}]`;
    fields(object(entry, label), ['id', 'name', 'startBar', 'endBar', 'function', 'energy', 'tension'], label);
    const section = {
      id: id(entry.id, `${label}.id`),
      name: text(entry.name, `${label}.name`, 64),
      startBar: integer(entry.startBar, 1, transport.bars, `${label}.startBar`),
      endBar: integer(entry.endBar, entry.startBar, transport.bars, `${label}.endBar`),
      function: text(entry.function, `${label}.function`, 128),
      energy: numberValue(entry.energy, 0, 1, `${label}.energy`),
      tension: numberValue(entry.tension, 0, 1, `${label}.tension`),
    };
    if (ids.has(section.id)) fail(`${label}.id duplicates ${section.id}`);
    if ((!migrated && section.startBar !== previousEnd + 1) || (migrated && section.startBar <= previousEnd)) fail('form sections overlap or are out of order');
    ids.add(section.id); previousEnd = section.endBar;
    return section;
  });
  if (!migrated && previousEnd !== transport.bars) fail('form must cover through transport.bars');
  return result;
}

function normalizeHarmony(raw, transport) {
  if (!Array.isArray(raw)) fail('harmony must be an array');
  let previous = -1;
  return raw.map((entry, index) => {
    const label = `harmony[${index}]`;
    fields(object(entry, label), ['step', 'duration', 'symbol', 'function', 'pitches'], label);
    const step = integer(entry.step, 0, transport.steps - 1, `${label}.step`);
    if (step < previous) fail('harmony must be ordered by step');
    previous = step;
    const pitches = strings(entry.pitches, `${label}.pitches`, 12);
    pitches.forEach((pitch, pitchIndex) => noteNameToMidi(pitch, `${label}.pitches[${pitchIndex}]`));
    return {
      step,
      duration: integer(entry.duration, 1, transport.steps - step, `${label}.duration`),
      symbol: text(entry.symbol, `${label}.symbol`, 32),
      function: optionalString(entry.function, '', `${label}.function`, 64),
      pitches,
    };
  });
}

function normalizeMotifs(raw) {
  if (!Array.isArray(raw)) fail('motifs must be an array');
  const ids = new Set();
  return raw.map((entry, index) => {
    const label = `motifs[${index}]`;
    fields(object(entry, label), ['id', 'intervals', 'rhythm', 'description'], label);
    const motifId = id(entry.id, `${label}.id`);
    if (ids.has(motifId)) fail(`${label}.id duplicates ${motifId}`);
    if (!Array.isArray(entry.intervals) || !entry.intervals.length || entry.intervals.length > 64) fail(`${label}.intervals must contain 1..64 entries`);
    const intervals = entry.intervals.map((value, i) => integer(value, -48, 48, `${label}.intervals[${i}]`));
    if (!Array.isArray(entry.rhythm) || entry.rhythm.length !== intervals.length) fail(`${label}.rhythm must match intervals length`);
    const rhythm = entry.rhythm.map((value, i) => integer(value, 1, 64, `${label}.rhythm[${i}]`));
    ids.add(motifId);
    return { id: motifId, intervals, rhythm, description: optionalString(entry.description, '', `${label}.description`, 256) };
  });
}

function normalizeMix(raw) {
  fields(object(raw, 'mix'), ['channels', 'masterVolume', 'defaultWave', 'fallbackPeriod', 'densityTarget'], 'mix');
  return {
    channels: integer(raw.channels, 1, 6, 'mix.channels'),
    masterVolume: raw.masterVolume == null ? 100 : integer(raw.masterVolume, 0, 100, 'mix.masterVolume'),
    defaultWave: raw.defaultWave == null ? 45 : integer(raw.defaultWave, 0, 45, 'mix.defaultWave'),
    fallbackPeriod: raw.fallbackPeriod == null ? 512 : integer(raw.fallbackPeriod, 1, 4095, 'mix.fallbackPeriod'),
    densityTarget: raw.densityTarget == null ? 'balanced' : text(raw.densityTarget, 'mix.densityTarget', 64),
  };
}

function normalizeReview(raw) {
  fields(object(raw, 'review'), ['audition', 'notes', 'passes', 'waivedFindingIds'], 'review');
  const allowed = new Set(['pending', 'complete']);
  if (!allowed.has(raw.audition)) fail('review.audition must be pending or complete');
  const passRaw = object(raw.passes, 'review.passes');
  fields(passRaw, REVIEW_PASSES, 'review.passes');
  const passes = {};
  REVIEW_PASSES.forEach((name) => {
    const label = `review.passes.${name}`;
    const value = object(passRaw[name], label);
    fields(value, ['status', 'notes'], label);
    if (!allowed.has(value.status)) fail(`${label}.status must be pending or complete`);
    passes[name] = { status: value.status, notes: optionalString(value.notes, '', `${label}.notes`, 512) };
  });
  return {
    audition: raw.audition,
    notes: raw.notes == null ? [] : strings(raw.notes, 'review.notes', 32),
    passes,
    waivedFindingIds: raw.waivedFindingIds == null ? [] : strings(raw.waivedFindingIds, 'review.waivedFindingIds', 64),
  };
}

function pitchFromEvent(entry, label, legacy) {
  if (legacy) {
    return { note: entry.note == null ? null : text(entry.note, `${label}.note`, 32), midi: null, period: integer(entry.periodLegacy, 1, 4095, `${label}.periodLegacy`) };
  }
  if (entry.note == null && entry.midi == null) fail(`${label} must specify note or midi`);
  const fromName = entry.note == null ? null : noteNameToMidi(entry.note, `${label}.note`);
  const midi = entry.midi == null ? fromName : integer(entry.midi, 0, 127, `${label}.midi`);
  if (fromName != null && fromName !== midi) fail(`${label}.note and midi do not match`);
  const period = midiNoteToPeriod(midi);
  if (entry.period != null && integer(entry.period, 1, 4095, `${label}.period`) !== period) fail(`${label}.period does not match calculated period ${period}`);
  return { note: entry.note == null ? midiToNoteName(midi) : entry.note, midi, period };
}

function normalizeParts(raw, transport, motifs, mix, migrated) {
  if (!Array.isArray(raw) || !raw.length) fail('parts must be a non-empty array');
  const motifIds = new Set(motifs.map((motif) => motif.id));
  const partIds = new Set();
  return raw.map((entry, index) => {
    const label = `parts[${index}]`;
    fields(object(entry, label), ['id', 'role', 'channel', 'range', 'wave', 'volume', 'noise', 'legacyExact', 'events'], label);
    const part = {
      id: id(entry.id, `${label}.id`),
      role: text(entry.role, `${label}.role`, 32),
      channel: integer(entry.channel, 0, 5, `${label}.channel`),
      noise: entry.noise === true,
      legacyExact: entry.legacyExact === true,
      volume: entry.volume == null ? 16 : integer(entry.volume, 0, 31, `${label}.volume`),
    };
    if (partIds.has(part.id)) fail(`${label}.id duplicates ${part.id}`);
    if (!PART_ROLES.has(part.role)) fail(`${label}.role is unknown`);
    if (part.channel >= mix.channels) fail(`${label}.channel must be less than mix.channels`);
    if (part.noise && part.channel < 4) fail(`${label}.noise is only valid on channel 4 or 5`);
    if (part.legacyExact !== migrated || (part.legacyExact && part.role !== 'legacy')) fail(`${label}.legacyExact does not match migration mode`);
    part.wave = part.noise ? null : (entry.wave == null ? mix.defaultWave : integer(entry.wave, 0, 45, `${label}.wave`));
    if (entry.range != null) {
      fields(object(entry.range, `${label}.range`), ['min', 'max'], `${label}.range`);
      const minMidi = noteNameToMidi(entry.range.min, `${label}.range.min`);
      const maxMidi = noteNameToMidi(entry.range.max, `${label}.range.max`);
      if (minMidi > maxMidi) fail(`${label}.range.min must not exceed max`);
      part.range = { min: entry.range.min, max: entry.range.max, minMidi, maxMidi };
    } else {
      part.range = null;
      if (!part.noise && !part.legacyExact) fail(`${label}.range is required for pitched parts`);
    }
    if (!Array.isArray(entry.events)) fail(`${label}.events must be an array`);
    part.events = entry.events.map((event, eventIndex) => {
      const eventLabel = `${label}.events[${eventIndex}]`;
      fields(object(event, eventLabel), ['step', 'duration', 'note', 'midi', 'period', 'volume', 'wave', 'articulation', 'motifRef', 'transform', 'noisePeriod', 'periodLegacy', 'noise'], eventLabel);
      const base = {
        step: integer(event.step, 0, transport.steps - 1, `${eventLabel}.step`),
        volume: event.volume == null ? part.volume : integer(event.volume, 0, 31, `${eventLabel}.volume`),
        wave: part.noise ? null : (event.wave == null ? part.wave : integer(event.wave, 0, 45, `${eventLabel}.wave`)),
      };
      if (part.legacyExact) {
        if (event.duration != null || event.motifRef != null) fail(`${eventLabel} legacy event may not use duration or motifRef`);
        return { ...base, duration: null, noise: event.noise === true, motifRef: null, transform: null, ...pitchFromEvent(event, eventLabel, true) };
      }
      const duration = integer(event.duration, 1, transport.steps - base.step, `${eventLabel}.duration`);
      const articulation = event.articulation == null ? 'normal' : text(event.articulation, `${eventLabel}.articulation`, 16);
      if (!ARTICULATIONS.has(articulation)) fail(`${eventLabel}.articulation is unknown`);
      if (part.noise) {
        if (event.note != null || event.midi != null || event.period != null || event.motifRef != null) fail(`${eventLabel} noise event may not contain pitched fields`);
        const noisePeriod = integer(event.noisePeriod, 1, 31, `${eventLabel}.noisePeriod`);
        return { ...base, duration, articulation, noise: true, motifRef: null, transform: null, note: null, midi: null, period: noisePeriod };
      }
      const motifRef = event.motifRef == null ? null : id(event.motifRef, `${eventLabel}.motifRef`);
      if (motifRef && !motifIds.has(motifRef)) fail(`${eventLabel}.motifRef is unknown`);
      let transform = null;
      if (motifRef) {
        const source = event.transform == null ? {} : object(event.transform, `${eventLabel}.transform`);
        fields(source, ['transpose', 'octave', 'inversion', 'rhythmScale', 'fragmentStart', 'fragmentLength'], `${eventLabel}.transform`);
        transform = {
          transpose: source.transpose == null ? 0 : integer(source.transpose, -48, 48, `${eventLabel}.transform.transpose`),
          octave: source.octave == null ? 0 : integer(source.octave, -4, 4, `${eventLabel}.transform.octave`),
          inversion: source.inversion === true,
          rhythmScale: source.rhythmScale == null ? 1 : integer(source.rhythmScale, 1, 8, `${eventLabel}.transform.rhythmScale`),
          fragmentStart: source.fragmentStart == null ? 0 : integer(source.fragmentStart, 0, 63, `${eventLabel}.transform.fragmentStart`),
          fragmentLength: source.fragmentLength == null ? null : integer(source.fragmentLength, 1, 64, `${eventLabel}.transform.fragmentLength`),
        };
      }
      const pitched = pitchFromEvent(event, eventLabel, false);
      if (part.range && (pitched.midi < part.range.minMidi || pitched.midi > part.range.maxMidi)) fail(`${eventLabel} pitch is outside part range`);
      return { ...base, duration, articulation, noise: false, motifRef, transform, ...pitched };
    });
    partIds.add(part.id);
    return part;
  });
}

function validateV2(raw) {
  const source = object(raw, 'score');
  fields(source, ROOT2, 'score');
  if (source.schemaVersion !== 2) fail('schemaVersion must be 2');
  const migrated = source.migration != null;
  let migration = null;
  if (migrated) {
    fields(object(source.migration, 'migration'), ['fromSchemaVersion', 'exact'], 'migration');
    if (source.migration.fromSchemaVersion !== 1 || source.migration.exact !== true) fail('migration must be exact from schemaVersion 1');
    migration = { fromSchemaVersion: 1, exact: true };
  }
  if (source.type !== 'psg-song' && source.type !== 'psg-sfx') fail('type must be psg-song or psg-sfx');
  if (source.loop !== (source.type === 'psg-song')) fail(`loop must be ${source.type === 'psg-song'} for ${source.type}`);
  const styleProfile = source.styleProfile == null ? null : text(source.styleProfile, 'styleProfile', 32);
  if (!migrated && !STYLE_PROFILES.has(styleProfile)) fail(`styleProfile must be one of ${[...STYLE_PROFILES].join(', ')}`);
  if (migrated && styleProfile != null) fail('exact migration must not infer styleProfile');
  const transport = normalizeTransport(source.transport, source.type, migrated);
  let tonality = null;
  if (source.tonality != null) {
    fields(object(source.tonality, 'tonality'), ['tonic', 'mode', 'scale'], 'tonality');
    noteNameToMidi(`${source.tonality.tonic}4`, 'tonality.tonic');
    tonality = {
      tonic: source.tonality.tonic,
      mode: text(source.tonality.mode, 'tonality.mode', 64),
      scale: source.tonality.scale == null ? [] : strings(source.tonality.scale, 'tonality.scale', 24),
    };
  } else if (!migrated) fail('tonality is required for new schemaVersion 2 scores');
  const mix = normalizeMix(source.mix);
  const motifs = normalizeMotifs(source.motifs);
  return {
    schemaVersion: 2,
    id: id(source.id),
    name: text(source.name, 'name', 128),
    type: source.type,
    loop: source.loop,
    intent: normalizeIntent(source.intent),
    styleProfile,
    transport,
    tonality,
    form: normalizeForm(source.form, transport, migrated),
    harmony: normalizeHarmony(source.harmony, transport),
    motifs,
    parts: normalizeParts(source.parts, transport, motifs, mix, migrated),
    mix,
    review: normalizeReview(source.review),
    migration,
  };
}

// V2_COMPILATION

function migrateV1(raw) {
  const old = validateV1(raw);
  const parts = [];
  for (let channel = 0; channel < old.channels; channel += 1) {
    const events = old.events.filter((event) => event.channel === channel).map((event) => ({
      step: event.step,
      periodLegacy: event.period,
      volume: event.volume,
      ...(event.note == null ? {} : { note: event.note }),
      ...(event.noise ? { noise: true } : { wave: event.wave }),
    }));
    if (events.length) parts.push({
      id: `legacy_ch${channel}`,
      role: 'legacy',
      channel,
      wave: old.wave,
      volume: 16,
      legacyExact: true,
      events,
    });
  }
  if (!parts.length) parts.push({ id: 'legacy_ch0', role: 'legacy', channel: 0, wave: old.wave, volume: 0, legacyExact: true, events: [] });
  const bars = Math.ceil(old.steps / old.stepsPerBar);
  return validateV2({
    schemaVersion: 2,
    id: old.id,
    name: old.name,
    type: old.type,
    loop: old.loop,
    intent: {
      purpose: 'Exact schemaVersion 1 migration',
      emotion: [],
      sceneFunction: 'Preserve playback without inferring musical intent',
      energyCurve: [],
      tensionCurve: [],
      hardwareTargets: ['generic'],
    },
    styleProfile: null,
    transport: {
      bpm: old.bpm,
      timeSignature: old.timeSignature,
      resolution: 4,
      bars,
      speed: old.speed,
      legacySteps: old.steps,
      legacyStepsPerBar: old.stepsPerBar,
      loop: { enabled: old.loop, startStep: 0, endStep: old.steps, intentionalDiscontinuity: false },
    },
    tonality: null,
    form: old.sections.map((section, index) => ({
      id: `legacy_section_${index + 1}`,
      name: section.name,
      startBar: section.startBar,
      endBar: section.endBar,
      function: 'legacy exact section metadata',
      energy: 0.5,
      tension: 0.5,
    })),
    harmony: [],
    motifs: [],
    parts,
    mix: {
      channels: old.channels,
      masterVolume: old.masterVolume,
      defaultWave: old.wave,
      fallbackPeriod: old.period,
      densityTarget: 'legacy exact',
    },
    review: {
      audition: 'pending',
      notes: ['Musical intent was not inferred during migration.'],
      passes: Object.fromEntries(REVIEW_PASSES.map((name) => [name, { status: 'pending', notes: 'Not inferred from v1 events.' }])),
      waivedFindingIds: [],
    },
    migration: { fromSchemaVersion: 1, exact: true },
  });
}

function publicScore(score) {
  return {
    schemaVersion: 2,
    id: score.id,
    name: score.name,
    type: score.type,
    loop: score.loop,
    intent: score.intent,
    styleProfile: score.styleProfile,
    transport: {
      bpm: score.transport.bpm,
      timeSignature: score.transport.timeSignature,
      resolution: score.transport.resolution,
      bars: score.transport.bars,
      speed: score.transport.speed,
      ...(score.migration ? { legacySteps: score.transport.steps, legacyStepsPerBar: score.transport.stepsPerBar } : {}),
      loop: score.transport.loop,
    },
    tonality: score.tonality,
    form: score.form,
    harmony: score.harmony,
    motifs: score.motifs,
    parts: score.parts.map((part) => ({
      id: part.id,
      role: part.role,
      channel: part.channel,
      ...(part.range ? { range: { min: part.range.min, max: part.range.max } } : {}),
      ...(part.noise ? { noise: true } : { wave: part.wave }),
      volume: part.volume,
      ...(part.legacyExact ? { legacyExact: true } : {}),
      events: part.events.map((event) => {
        if (part.legacyExact) return {
          step: event.step,
          periodLegacy: event.period,
          volume: event.volume,
          ...(event.note == null ? {} : { note: event.note }),
          ...(event.noise ? { noise: true } : { wave: event.wave }),
        };
        const result = {
          step: event.step,
          duration: event.duration,
          ...(event.note == null ? {} : { note: event.note }),
          volume: event.volume,
          ...(event.noise ? { noisePeriod: event.period } : { wave: event.wave }),
          articulation: event.articulation,
        };
        if (event.motifRef) {
          result.motifRef = event.motifRef;
          result.transform = event.transform;
        }
        return result;
      }),
    })),
    mix: score.mix,
    review: score.review,
    ...(score.migration ? { migration: score.migration } : {}),
  };
}

function gate(duration, articulation) {
  if (articulation === 'staccato') return Math.max(1, Math.floor(duration / 2));
  if (articulation === 'normal') return Math.max(1, Math.round(duration * 0.8));
  return duration;
}

function expand(score) {
  if (score.migration) {
    const occupied = new Set();
    const pattern = [];
    score.parts.forEach((part) => part.events.forEach((event, eventIndex) => {
      const key = `${event.step}:${part.channel}`;
      if (occupied.has(key)) fail(`legacyExact events duplicate step ${event.step}, channel ${part.channel}`);
      occupied.add(key);
      pattern.push({
        step: event.step,
        channel: part.channel,
        period: event.period,
        volume: event.volume,
        wave: event.noise ? null : event.wave,
        noise: event.noise,
        note: event.note,
        midi: null,
        source: { partId: part.id, eventIndex, legacyExact: true },
      });
    }));
    pattern.sort((a, b) => a.step - b.step || a.channel - b.channel);
    return { notes: [], pattern };
  }
  const motifs = new Map(score.motifs.map((motif) => [motif.id, motif]));
  const notes = [];
  score.parts.forEach((part) => part.events.forEach((event, eventIndex) => {
    if (!event.motifRef) {
      notes.push({ ...event, channel: part.channel, source: { partId: part.id, eventIndex } });
      return;
    }
    const motif = motifs.get(event.motifRef);
    const transform = event.transform;
    const start = transform.fragmentStart;
    const end = transform.fragmentLength == null ? motif.intervals.length : Math.min(motif.intervals.length, start + transform.fragmentLength);
    const occurrence = `part ${part.id}, event ${eventIndex}, step ${event.step}`;
    if (start >= end || start >= motif.intervals.length) fail(`motif ${motif.id} selects an empty fragment at ${occurrence}`);
    let cursor = event.step;
    let total = 0;
    for (let index = start; index < end; index += 1) {
      const interval = (transform.inversion ? -motif.intervals[index] : motif.intervals[index]) + transform.transpose + (transform.octave * 12);
      const midi = event.midi + interval;
      if (midi < 0 || midi > 127) fail(`motif ${motif.id} expands outside MIDI range at ${occurrence}, motif index ${index}`);
      const duration = motif.rhythm[index] * transform.rhythmScale;
      total += duration;
      if (cursor + duration > score.transport.steps) fail(`motif ${motif.id} extends past transport.steps at ${occurrence}`);
      if (part.range && (midi < part.range.minMidi || midi > part.range.maxMidi)) fail(`motif ${motif.id} expands to ${midiToNoteName(midi)} outside part ${part.id} range at ${occurrence}, motif index ${index}`);
      notes.push({
        step: cursor,
        duration,
        note: midiToNoteName(midi),
        midi,
        period: midiNoteToPeriod(midi),
        volume: event.volume,
        wave: event.wave,
        noise: false,
        articulation: event.articulation,
        channel: part.channel,
        source: { partId: part.id, eventIndex, motifRef: motif.id, motifIndex: index },
      });
      cursor += duration;
    }
    if (total !== event.duration) fail(`motif ${motif.id} expanded duration ${total} does not match occurrence duration ${event.duration} at ${occurrence}`);
  }));
  const byChannel = new Map();
  notes.forEach((note) => {
    if (!byChannel.has(note.channel)) byChannel.set(note.channel, []);
    byChannel.get(note.channel).push(note);
  });
  byChannel.forEach((channelNotes, channel) => {
    channelNotes.sort((a, b) => a.step - b.step || a.source.partId.localeCompare(b.source.partId));
    for (let index = 1; index < channelNotes.length; index += 1) {
      const previous = channelNotes[index - 1];
      if (channelNotes[index].step < previous.step + previous.duration) fail(`channel ${channel} overlap at step ${channelNotes[index].step}`);
    }
  });
  const attacks = new Map();
  const offs = new Map();
  notes.forEach((note) => {
    const attackKey = `${note.step}:${note.channel}`;
    if (attacks.has(attackKey)) fail(`duplicate attack at step ${note.step}, channel ${note.channel}`);
    attacks.set(attackKey, note);
    const offStep = note.step + gate(note.duration, note.articulation);
    if (offStep < score.transport.steps && !offs.has(`${offStep}:${note.channel}`)) offs.set(`${offStep}:${note.channel}`, note);
  });
  const keys = new Set([...attacks.keys(), ...offs.keys()]);
  const pattern = [...keys].map((key) => {
    if (attacks.has(key)) {
      const note = attacks.get(key);
      return { step: note.step, channel: note.channel, period: note.period, volume: note.volume, wave: note.wave, noise: note.noise, note: note.note, midi: note.midi, source: note.source };
    }
    const note = offs.get(key);
    return { step: Number(key.split(':')[0]), channel: note.channel, period: note.period, volume: 0, wave: note.wave, noise: note.noise, note: null, midi: null, source: { ...note.source, noteOff: true } };
  }).sort((a, b) => a.step - b.step || a.channel - b.channel);
  if (pattern.length > MAX_EVENTS) fail(`expanded pattern contains ${pattern.length} events; maximum is ${MAX_EVENTS}`);
  return { notes: notes.sort((a, b) => a.step - b.step || a.channel - b.channel), pattern };
}

function outputEvent(event) {
  const result = { step: event.step, channel: event.channel, period: event.period, volume: event.volume };
  if (event.note != null) result.note = event.note;
  if (event.noise) result.noise = 1;
  else result.wave = event.wave;
  return result;
}

function documentFor(score, scoreHash, expanded) {
  const document = {
    version: 2,
    assets: [{
      id: score.id,
      type: score.type,
      name: score.name,
      source: '',
      options: {
        kind: score.type === 'psg-song' ? 'song' : 'sfx',
        bpm: score.transport.bpm,
        speed: score.transport.speed,
        period: score.mix.fallbackPeriod,
        wave: score.mix.defaultWave,
        channels: score.mix.channels,
        steps: score.transport.steps,
        volume: score.mix.masterVolume,
        loop: score.loop,
        timeSignature: score.transport.timeSignature,
        bars: score.transport.bars,
        stepsPerBar: score.transport.stepsPerBar,
        sections: score.form.map((section) => ({
          name: section.name,
          startBar: section.startBar,
          endBar: section.endBar,
          startStep: (section.startBar - 1) * score.transport.stepsPerBar,
        })),
        pattern: expanded.pattern.map(outputEvent),
      },
    }],
  };
  if (!score.migration) document.authoring = { scoreSchemaVersion: 2, scoreSha256: scoreHash, generatorVersion: GENERATOR_VERSION };
  return document;
}

function compileScore(raw) {
  if (!raw || typeof raw !== 'object') fail('score must be an object');
  const sourceVersion = raw.schemaVersion;
  if (sourceVersion !== 1 && sourceVersion !== 2) fail('schemaVersion must be 1 or 2');
  const score = sourceVersion === 1 ? migrateV1(raw) : validateV2(raw);
  const normalized = publicScore(score);
  const scoreText = canonical(normalized);
  const scoreHash = sha256(scoreText);
  const expanded = expand(score);
  return {
    score,
    publicScore: normalized,
    scoreText,
    scoreHash,
    expanded,
    document: documentFor(score, scoreHash, expanded),
    sourceSchemaVersion: sourceVersion,
  };
}

module.exports = {
  GENERATOR_VERSION, MAX_EVENTS, MAX_STEPS, PSG_CLOCK, REVIEW_PASSES,
  STYLE_PROFILES, canonical, compileScore, midiNoteToPeriod, midiToNoteName,
  migrateV1, noteNameToMidi, sha256, validateV1, validateV2,
};
