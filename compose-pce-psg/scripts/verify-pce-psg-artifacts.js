#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const scoreLib = require('./pce-score.js');

function fail(message) { throw new Error(message); }
function main(argv = process.argv.slice(2)) {
  if (argv.length !== 2 || argv[0] !== '--audit') fail('usage: --audit <id.audit.json>');
  const auditPath = path.resolve(argv[1]);
  const directory = path.dirname(auditPath);
  const auditText = fs.readFileSync(auditPath, 'utf8');
  const audit = JSON.parse(auditText);
  const scorePath = path.join(directory, audit.artifacts.score);
  const psgPath = path.join(directory, audit.artifacts.psg);
  const markdownPath = path.join(directory, audit.artifacts.auditMarkdown);
  const scoreHash = scoreLib.sha256(fs.readFileSync(scorePath));
  const psgHash = scoreLib.sha256(fs.readFileSync(psgPath));
  if (scoreHash !== audit.hashes.scoreSha256) fail(`stale score: expected ${audit.hashes.scoreSha256}, got ${scoreHash}`);
  if (psgHash !== audit.hashes.psgSha256) fail(`stale PSG: expected ${audit.hashes.psgSha256}, got ${psgHash}`);
  const psg = JSON.parse(fs.readFileSync(psgPath, 'utf8'));
  if (psg.authoring && psg.authoring.scoreSha256 !== scoreHash) fail('PSG authoring score SHA does not match score file');
  const markdown = fs.readFileSync(markdownPath, 'utf8');
  const auditHash = scoreLib.sha256(auditText);
  if (!markdown.includes(`Audit SHA-256: \`${auditHash}\``)) fail('stale audit Markdown: audit SHA is missing or mismatched');
  process.stdout.write(`verified ${audit.id}\n`);
  return { scorePath, psgPath, auditPath, markdownPath };
}
if (require.main === module) {
  try { main(); } catch (error) {
    process.stderr.write(`verify-pce-psg-artifacts: ${error.message}\n`);
    process.exitCode = 1;
  }
}
module.exports = { main };
