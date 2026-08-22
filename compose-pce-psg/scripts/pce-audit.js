'use strict';

const scoreLib = require('./pce-score.js');

const PSG_EVENT_BYTES = 8;

function finding(ruleId, severity, message, location = 'score', details = {}) {
  return { ruleId, severity, location, message, details };
}

function partRole(score, note) {
  return score.parts.find((part) => part.id === note.source.partId)?.role || 'unknown';
}

function harmonyAt(score, step) {
  return score.harmony.find((entry) => step >= entry.step && step < entry.step + entry.duration) || null;
}

function sectionAt(score, step) {
  const bar = Math.floor(step / score.transport.stepsPerBar) + 1;
  return score.form.find((section) => bar >= section.startBar && bar <= section.endBar) || null;
}

function voiceLeadingCost(harmony) {
  let total = 0;
  let transitions = 0;
  for (let index = 1; index < harmony.length; index += 1) {
    const from = harmony[index - 1].pitches.map(scoreLib.noteNameToMidi);
    const to = harmony[index].pitches.map(scoreLib.noteNameToMidi);
    if (!from.length || !to.length) continue;
    total += from.reduce((sum, pitch) => sum + Math.min(...to.map((next) => Math.abs(next - pitch))), 0) / from.length;
    transitions += 1;
  }
  return transitions ? Number((total / transitions).toFixed(3)) : 0;
}

function systemCardRepresentation(pattern) {
  const biosPeriods = Array.from({ length: 84 }, (_, index) => scoreLib.midiNoteToPeriod(index + 24));
  const errors = pattern.filter((event) => !event.noise && event.volume > 0).map((event) => {
    let best = Infinity;
    biosPeriods.forEach((base) => {
      const detune = Math.max(-128, Math.min(127, event.period - base));
      best = Math.min(best, Math.abs(event.period - (base + detune)));
    });
    return best;
  }).filter((error) => error > 0);
  return {
    approximationCount: errors.length,
    maximumPeriodError: errors.length ? Math.max(...errors) : 0,
  };
}

function melodyMetrics(score, notes) {
  const leaps = [];
  score.parts.filter((part) => part.role === 'melody').forEach((part) => {
    const sequence = notes.filter((note) => note.source.partId === part.id).sort((a, b) => a.step - b.step);
    for (let index = 1; index < sequence.length; index += 1) leaps.push(Math.abs(sequence[index].midi - sequence[index - 1].midi));
  });
  return {
    largestLeap: leaps.length ? Math.max(...leaps) : 0,
    meanLeap: leaps.length ? Number((leaps.reduce((sum, value) => sum + value, 0) / leaps.length).toFixed(3)) : 0,
  };
}

function analyzeLoop(score, expanded, findings) {
  if (!score.loop) return;
  const first = new Map();
  const last = new Map();
  expanded.pattern.forEach((event) => {
    if (!first.has(event.channel)) first.set(event.channel, event);
    last.set(event.channel, event);
  });
  for (const [channel, tail] of last) {
    const head = first.get(channel);
    if (tail.volume > 0 && head.step > 0) {
      findings.push(finding('loop-hanging-note', 'profile-warning', `Channel ${channel} remains audible across a silent loop prefix.`, `channel.${channel}`, { firstStep: head.step, lastStep: tail.step }));
    }
    if (tail.volume > 0 && head.step === 0 && !tail.noise && !head.noise) {
      if (Number.isInteger(tail.midi) && Number.isInteger(head.midi) && Math.abs(tail.midi - head.midi) > 12) {
        findings.push(finding('loop-pitch-seam', 'profile-warning', `Channel ${channel} crosses more than an octave at the loop seam.`, `channel.${channel}`, { semitones: Math.abs(tail.midi - head.midi) }));
      }
      if (tail.wave !== head.wave) findings.push(finding('loop-timbre-seam', 'profile-warning', `Channel ${channel} changes wave at the loop seam.`, `channel.${channel}`, { from: tail.wave, to: head.wave }));
      if (Math.abs(tail.volume - head.volume) > 12) findings.push(finding('loop-volume-seam', 'profile-warning', `Channel ${channel} changes volume abruptly at the loop seam.`, `channel.${channel}`, { from: tail.volume, to: head.volume }));
    }
  }
  if (score.transport.loop.intentionalDiscontinuity) {
    findings.filter((entry) => entry.ruleId.startsWith('loop-')).forEach((entry) => {
      entry.severity = 'information';
      entry.details.intentionalDiscontinuity = true;
    });
  }
}

function analyzeProfile(score, expanded, metrics, findings) {
  const profile = score.styleProfile;
  const notes = expanded.notes.filter((note) => !note.noise && note.volume > 0);
  const melody = notes.filter((note) => partRole(score, note) === 'melody');
  if (score.tonality.scale.length) {
    const declared = new Set(score.tonality.scale.map((pitch) => scoreLib.noteNameToMidi(`${pitch}4`) % 12));
    const outside = notes.filter((note) => !declared.has(note.midi % 12));
    if (outside.length) {
      const pitchNames = [...new Set(outside.map((note) => scoreLib.midiToNoteName(note.midi).replace(/-?\d+$/, '')))].sort();
      const severity = (profile === 'tonal' || profile === 'modal') && (outside.length >= 2 || outside.length / notes.length > 0.1)
        ? 'profile-warning'
        : 'information';
      findings.push(finding('expanded-pitch-outside-scale', severity, `Expanded notes use pitch classes outside the declared scale: ${pitchNames.join(', ')}. Record chromatic intent or revise the motif transformation.`, 'tonality.scale', {
        count: outside.length,
        ratio: Number((outside.length / notes.length).toFixed(3)),
        pitchClasses: pitchNames,
        occurrences: outside.slice(0, 16).map((note) => ({ step: note.step, partId: note.source.partId, note: note.note, motifRef: note.source.motifRef || null })),
      }));
    }
  }
  if ((profile === 'tonal' || profile === 'modal') && metrics.largestMelodyLeap > 12) {
    findings.push(finding('melody-large-leap', 'profile-warning', `Melody contains a ${metrics.largestMelodyLeap}-semitone leap. Review recovery and singability.`, 'parts[role=melody]'));
  }
  if (profile === 'tonal' && melody.length && score.harmony.length) {
    let strong = 0;
    let nonChord = 0;
    melody.forEach((note) => {
      if (note.step % score.transport.resolution) return;
      const harmony = harmonyAt(score, note.step);
      if (!harmony || !harmony.pitches.length) return;
      strong += 1;
      const chord = new Set(harmony.pitches.map((pitch) => scoreLib.noteNameToMidi(pitch) % 12));
      if (!chord.has(note.midi % 12)) nonChord += 1;
    });
    if (strong >= 4 && nonChord / strong > 0.4) {
      findings.push(finding('tonal-strong-beat-instability', 'profile-warning', 'More than 40% of analyzed strong-beat melody notes are outside declared chord pitches.', 'harmony', { strong, nonChord }));
    }
    let embellishments = 0;
    let unresolved = 0;
    melody.forEach((note, index) => {
      const harmony = harmonyAt(score, note.step);
      if (!harmony || !harmony.pitches.length) return;
      const chord = new Set(harmony.pitches.map((pitch) => scoreLib.noteNameToMidi(pitch) % 12));
      if (chord.has(note.midi % 12)) return;
      embellishments += 1;
      const next = melody[index + 1];
      const nextHarmony = next && harmonyAt(score, next.step);
      const nextChord = new Set((nextHarmony?.pitches || []).map((pitch) => scoreLib.noteNameToMidi(pitch) % 12));
      if (!next || Math.abs(next.midi - note.midi) > 2 || !nextChord.has(next.midi % 12)) unresolved += 1;
    });
    if (embellishments >= 3 && unresolved / embellishments > 0.5) {
      findings.push(finding('tonal-nonchord-resolution', 'profile-warning', 'Most analyzed non-chord melody notes do not resolve by step into a declared chord pitch.', 'parts[role=melody]', { embellishments, unresolved }));
    }
    if (melody.length >= 8) {
      const top = Math.max(...melody.map((note) => note.midi));
      const topCount = melody.filter((note) => note.midi === top).length;
      if (topCount > 2) findings.push(finding('melody-climax-diffuse', 'profile-warning', 'The melody reaches its highest pitch repeatedly; confirm that the climax remains purposeful.', 'parts[role=melody]', { top: scoreLib.midiToNoteName(top), topCount }));
    }
  }
  const density = {
    tonal: [2, 32],
    modal: [2, 32],
    ambient: [0, 16],
    action: [8, 64],
    'sfx-jingle': [0, 96],
  }[profile];
  if (metrics.densityPerBar < density[0]) findings.push(finding('profile-density-low', 'profile-warning', `Onset density ${metrics.densityPerBar}/bar is low for ${profile}.`, 'parts'));
  if (metrics.densityPerBar > density[1]) findings.push(finding('profile-density-high', 'profile-warning', `Onset density ${metrics.densityPerBar}/bar is high for ${profile}.`, 'parts'));
  if (score.form.length > 1 && ['tonal', 'modal', 'action'].includes(profile)) {
    const stats = score.form.map((section) => {
      const sectionNotes = notes.filter((note) => sectionAt(score, note.step)?.id === section.id);
      return {
        id: section.id,
        count: sectionNotes.length,
        averageMidi: sectionNotes.length ? sectionNotes.reduce((sum, note) => sum + note.midi, 0) / sectionNotes.length : null,
      };
    });
    const averages = stats.map((entry) => entry.averageMidi).filter(Number.isFinite);
    const registerSpread = averages.length ? Math.max(...averages) - Math.min(...averages) : 0;
    const energySpread = Math.max(...score.form.map((section) => section.energy)) - Math.min(...score.form.map((section) => section.energy));
    const tensionSpread = Math.max(...score.form.map((section) => section.tension)) - Math.min(...score.form.map((section) => section.tension));
    if (new Set(stats.map((entry) => entry.count)).size === 1 && registerSpread < 2 && energySpread < 0.08 && tensionSpread < 0.08) {
      findings.push(finding('section-contrast-low', 'profile-warning', 'Declared sections have nearly identical onset count and register. Confirm another audible contrast dimension.', 'form', { stats }));
    }
  }
  const melodyParts = score.parts.filter((part) => part.role === 'melody' && part.range);
  const bassParts = score.parts.filter((part) => part.role === 'bass' && part.range);
  melodyParts.forEach((melodyPart) => bassParts.forEach((bassPart) => {
    if (bassPart.range.maxMidi - melodyPart.range.minMidi >= 3) {
      findings.push(finding('arrangement-range-overlap', 'profile-warning', `Bass ${bassPart.id} overlaps melody ${melodyPart.id} range.`, `parts.${bassPart.id}`));
    }
  }));
  const signatures = [];
  for (let bar = 0; bar < score.transport.bars; bar += 1) {
    const start = bar * score.transport.stepsPerBar;
    signatures.push(expanded.pattern.filter((event) => event.step >= start && event.step < start + score.transport.stepsPerBar)
      .map((event) => `${event.step - start}:${event.channel}:${event.period}:${event.volume}:${event.wave ?? 'n'}`).join('|'));
  }
  if (score.transport.bars >= 4 && new Set(signatures).size === 1 && profile !== 'ambient' && profile !== 'sfx-jingle') {
    findings.push(finding('repetition-exact-all-bars', profile === 'action' ? 'information' : 'profile-warning', 'Every bar is event-identical. Review macro/meso variation and repetition fatigue.', 'form'));
  }
  if (profile === 'action' && metrics.onsetLockRatio >= 0.6) {
    findings.push(finding('action-onset-lock-high', 'information', 'Many attack steps are shared by multiple channels. Review whether coordinated hits leave enough rhythmic independence.', 'parts', { onsetLockRatio: metrics.onsetLockRatio }));
    if (metrics.durationSeconds < 15) {
      findings.push(finding('short-loop-fatigue-review', 'information', 'This dense action loop is under 15 seconds and highly onset-locked. Repeated audition is recommended for fatigue.', 'transport', { durationSeconds: metrics.durationSeconds, onsetLockRatio: metrics.onsetLockRatio }));
    }
  }
}

function analyze(compiled) {
  const { score, expanded } = compiled;
  const notes = expanded.notes.filter((note) => !note.noise && note.volume > 0);
  const noise = expanded.notes.filter((note) => note.noise && note.volume > 0);
  const melody = melodyMetrics(score, notes);
  const attackSteps = new Map();
  expanded.notes.filter((note) => note.volume > 0).forEach((note) => {
    if (!attackSteps.has(note.step)) attackSteps.set(note.step, new Set());
    attackSteps.get(note.step).add(note.channel);
  });
  const lockedSteps = [...attackSteps.values()].filter((channels) => channels.size > 1).length;
  const systemCard = systemCardRepresentation(expanded.pattern);
  const metrics = {
    steps: score.transport.steps,
    bars: score.transport.bars,
    durationSeconds: Number(((score.transport.steps * 15) / score.transport.bpm).toFixed(3)),
    patternEvents: expanded.pattern.length,
    serializedPatternBytes: expanded.pattern.length * PSG_EVENT_BYTES,
    pitchedNotes: notes.length,
    noiseHits: noise.length,
    noteOffs: expanded.pattern.filter((event) => event.volume === 0).length,
    activeChannels: [...new Set(expanded.pattern.map((event) => event.channel))].sort(),
    densityPerBar: Number(((notes.length + noise.length) / score.transport.bars).toFixed(3)),
    syncopationRatio: notes.length ? Number((notes.filter((note) => note.step % score.transport.resolution !== 0).length / notes.length).toFixed(3)) : 0,
    onsetLockRatio: attackSteps.size ? Number((lockedSteps / attackSteps.size).toFixed(3)) : 0,
    noteRange: notes.length ? { min: scoreLib.midiToNoteName(Math.min(...notes.map((note) => note.midi))), max: scoreLib.midiToNoteName(Math.max(...notes.map((note) => note.midi))) } : null,
    largestMelodyLeap: melody.largestLeap,
    meanMelodyLeap: melody.meanLeap,
    voiceLeadingCost: voiceLeadingCost(score.harmony),
    motifOccurrences: score.parts.reduce((sum, part) => sum + part.events.filter((event) => event.motifRef).length, 0),
    targetMedia: {
      hucard: { periodRangeValid: true },
      cdrom2SystemCard: systemCard,
    },
  };
  const findings = [];
  if (score.migration) {
    findings.push(finding('legacy-musical-analysis-skipped', 'information', 'Musical intent was not inferred; only structural PSG metrics are reported.', 'migration'));
  } else {
    analyzeProfile(score, expanded, metrics, findings);
    analyzeLoop(score, expanded, findings);
  }
  if (score.intent.hardwareTargets.some((target) => target === 'cdrom2' || target === 'both')
    && systemCard.approximationCount > 0) {
    findings.push(finding('target-period-approximation', 'profile-warning', 'Some periods require approximation in the System Card PSG package.', 'intent.hardwareTargets', systemCard));
  }
  const waived = new Set(score.review.waivedFindingIds);
  findings.forEach((entry) => { entry.disposition = waived.has(entry.ruleId) ? 'waived' : 'open'; });
  const warnings = findings.filter((entry) => entry.severity === 'profile-warning' && entry.disposition === 'open');
  const pendingPasses = scoreLib.REVIEW_PASSES.filter((name) => score.review.passes[name].status !== 'complete');
  const musicalReview = score.migration ? 'pending' : (warnings.length || pendingPasses.length ? 'concerns' : 'pass');
  return {
    metrics,
    findings,
    selfReview: { passes: score.review.passes, pendingPasses, notes: score.review.notes },
    status: {
      technical: 'pass',
      musicalReview,
      audition: score.review.audition,
      disposition: musicalReview === 'pass' && score.review.audition === 'complete' ? 'complete' : 'provisional',
    },
  };
}

function build(compiled, psgText) {
  const analysis = analyze(compiled);
  return {
    schemaVersion: 1,
    generatorVersion: scoreLib.GENERATOR_VERSION,
    id: compiled.score.id,
    styleProfile: compiled.score.styleProfile,
    sourceSchemaVersion: compiled.sourceSchemaVersion,
    hashes: { scoreSha256: compiled.scoreHash, psgSha256: scoreLib.sha256(psgText) },
    artifacts: {
      score: `${compiled.score.id}.score.json`,
      psg: `${compiled.score.id}.psg.json`,
      audit: `${compiled.score.id}.audit.json`,
      auditMarkdown: `${compiled.score.id}.audit.md`,
    },
    ...analysis,
  };
}

function markdown(audit, auditHash) {
  const lines = [
    `# Music audit: ${audit.id}`, '',
    `- Technical: ${audit.status.technical}`,
    `- Musical review: ${audit.status.musicalReview}`,
    `- Audition: ${audit.status.audition}`,
    `- Disposition: ${audit.status.disposition}`,
    `- Score SHA-256: \`${audit.hashes.scoreSha256}\``,
    `- PSG SHA-256: \`${audit.hashes.psgSha256}\``,
    `- Audit SHA-256: \`${auditHash}\``, '',
    '## Metrics', '',
    `- ${audit.metrics.bars} bars, ${audit.metrics.steps} steps, ${audit.metrics.durationSeconds} seconds`,
    `- ${audit.metrics.patternEvents} events / ${audit.metrics.serializedPatternBytes} serialized bytes`,
    `- ${audit.metrics.pitchedNotes} pitched notes, ${audit.metrics.noiseHits} noise hits, ${audit.metrics.densityPerBar} onsets/bar`, '',
    '## Findings', '',
  ];
  if (!audit.findings.length) lines.push('- None.');
  audit.findings.forEach((entry) => lines.push(`- **${entry.severity}** \`${entry.ruleId}\` at \`${entry.location}\`: ${entry.message}${entry.disposition === 'waived' ? ' (waived)' : ''}`));
  lines.push('', '## Self-review', '');
  scoreLib.REVIEW_PASSES.forEach((name) => lines.push(`- ${name}: ${audit.selfReview.passes[name].status}${audit.selfReview.passes[name].notes ? ` - ${audit.selfReview.passes[name].notes}` : ''}`));
  lines.push('', '> Static analysis cannot prove musical naturalness. A pending audition keeps the result provisional.', '');
  return `${lines.join('\n')}\n`;
}

module.exports = { analyze, build, markdown };
