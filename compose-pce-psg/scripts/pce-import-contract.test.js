'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const composer = require('./compose-pce-psg.js');

const pceRoot = process.env.PCE_GAME_EDITOR_DIR;

test('generated PSG is accepted by current PCE asset manager and both serializers', { skip: !pceRoot }, () => {
  const assetManager = require(path.join(pceRoot, 'pce-asset-manager.js'));
  const systemCardPsg = require(path.join(pceRoot, 'pce-system-card-psg.js'));
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'compose-pce-import-'));
  const projectDir = path.join(workspace, 'project');
  const outputDir = path.join(workspace, 'output');
  fs.mkdirSync(projectDir);
  const template = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'assets', 'score-template.json'), 'utf8'));
  const artifacts = composer.generateArtifacts(template);
  const sourcePath = path.join(outputDir, `${template.id}.psg.json`);
  fs.mkdirSync(outputDir);
  fs.writeFileSync(sourcePath, artifacts.psgText);
  const inspected = assetManager.inspectPsgJson(projectDir, { sourcePath });
  assert.equal(inspected.summary.id, template.id);
  assert.equal(inspected.summary.eventCount, artifacts.audit.metrics.patternEvents);
  assert.equal(assetManager.psgPatternBytes(inspected.asset).length, artifacts.audit.metrics.serializedPatternBytes);
  const packageResult = systemCardPsg.compileSystemCardPsgPackage(inspected.asset);
  assert.ok(packageResult.bytes.length > 0);
  assert.equal(packageResult.bus, 'bgm');
});
