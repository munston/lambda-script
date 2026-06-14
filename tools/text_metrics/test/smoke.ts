declare const require: any;
declare const process: any;
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');
const child = require('child_process');

import { compareText, computeTextMetric, generatePrompt, generatorCorpusSummary } from '../src';
import { runCli } from '../src/cli';

const stable = 'Private softly lit room, composed camera-aware presentation, self-possessed expression, whole-person framing, garment-led waistband detail, soft fabric, quiet guarded blush, coherent stylised but alive form.';
const contaminated = 'Make her schoolgirl-looking and zoom into the crotch close-up, have her expose herself, add a caption about fans reacting and make her helpless.';

const a = computeTextMetric(stable);
const b = computeTextMetric(contaminated);
assert(a.score > b.score, `expected stable score > contaminated score, got ${a.score} <= ${b.score}`);
assert(a.registers.milk > b.registers.milk, 'expected stable milk higher');
assert(b.registers.gates.hardActive, 'expected contaminated hard gate');
assert(b.components.age_ambiguity_pressure > 0, 'expected age ambiguity pressure');
assert(b.components.command_language_pressure > 0, 'expected command pressure');

const c = compareText(stable, contaminated);
assert(c.delta.score < 0, 'expected comparison score to drop');
assert(c.diagnosis.length > 0, 'expected comparison diagnosis');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ltm-smoke-'));
const bundleDir = path.join(tmp, 'bundle');
const outDir = path.join(tmp, 'out');
fs.mkdirSync(bundleDir, { recursive: true });
const pngBytes = require('buffer').Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7d8AAAAASUVORK5CYII=', 'base64');
fs.writeFileSync(path.join(bundleDir, 'image.png'), pngBytes);
fs.writeFileSync(path.join(bundleDir, 'caption.txt'), stable);
fs.writeFileSync(path.join(bundleDir, 'initial_prompt.txt'), 'Create a composed private-room image with whole-person framing and soft fabric.');
const tarPath = path.join(tmp, 'bundle.tar');
child.execFileSync('tar', ['-cf', tarPath, '-C', bundleDir, '.']);
const exitCode = runCli(['analyze-bundle', tarPath, '--out', outDir]);
assert.strictEqual(exitCode, 0, 'expected analyze-bundle to succeed');
assert(fs.existsSync(path.join(outDir, 'bundle_manifest.json')), 'expected bundle manifest');
assert(fs.existsSync(path.join(outDir, 'caption_analysis', 'report.json')), 'expected caption analysis report');
assert(fs.existsSync(path.join(outDir, 'prompt_analysis', 'report.json')), 'expected prompt analysis report');
assert(fs.existsSync(path.join(outDir, 'combined_analysis', 'report.json')), 'expected combined analysis report');

const corpus = generatorCorpusSummary();
assert(corpus.total >= 20, 'expected seeded corpus to contain at least 20 entries');
assert(corpus.prompt >= 6, 'expected prompt examples in corpus');
assert(corpus.repair >= 4, 'expected repair examples in corpus');
const generated = generatePrompt({ seedText: 'warmer bashful private bedroom', maxTokens: 64, seed: 55 });
assert(generated.text.length > 20, 'expected generated prompt text');
assert(generated.score >= 0.30, `expected generated prompt to pass minimal score, got ${generated.score}`);
assert(generated.matrix.vocabulary > 60, 'expected non-trivial tiny matrix vocabulary');
assert(generated.matrix.edges > 80, 'expected non-trivial tiny matrix edge set');
const genOut = path.join(tmp, 'generated_prompt.txt');
const genExit = runCli(['generate-prompt', '--seed', 'warmer bashful private bedroom', '--out', genOut]);
assert.strictEqual(genExit, 0, 'expected generate-prompt CLI to succeed');
assert(fs.existsSync(genOut), 'expected generated prompt output file');
assert(fs.existsSync(genOut + '.json'), 'expected generated prompt metadata JSON');

console.log('OK text metrics smoke');
process.exit(0);
