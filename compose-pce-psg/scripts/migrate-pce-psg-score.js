#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const scoreLib = require('./pce-score.js');

function fail(message) { throw new Error(message); }
function args(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    if (key !== '--score' && key !== '--out') fail(`unknown argument: ${key}`);
    if (!argv[index + 1]) fail(`${key} requires a value`);
    result[key.slice(2)] = argv[index + 1];
  }
  if (!result.score || !result.out) fail('--score and --out are required');
  return result;
}
function main(argv = process.argv.slice(2)) {
  const options = args(argv);
  const source = JSON.parse(fs.readFileSync(path.resolve(options.score), 'utf8'));
  if (source.schemaVersion !== 1) fail('migration input must use schemaVersion 1');
  const migrated = scoreLib.compileScore(source);
  const outputDirectory = path.resolve(options.out);
  fs.mkdirSync(outputDirectory, { recursive: true });
  const outputPath = path.join(outputDirectory, `${migrated.score.id}.score.json`);
  fs.writeFileSync(outputPath, migrated.scoreText, 'utf8');
  process.stdout.write(`${outputPath}\n`);
  return outputPath;
}
if (require.main === module) {
  try { main(); } catch (error) {
    process.stderr.write(`migrate-pce-psg-score: ${error.message}\n`);
    process.exitCode = 1;
  }
}
module.exports = { main };
