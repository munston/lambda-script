declare const require: any;
const assert = require('assert');

import { evaluateTextGates, passesTextGates } from '../src/gates';

function categories(text: string): string[] {
  return evaluateTextGates(text).findings.map(item => item.category).sort();
}

function assertHard(text: string, category: string): void {
  const report = evaluateTextGates(text);
  assert.strictEqual(report.hardBlocked, true, `expected hard block for ${category}`);
  assert.strictEqual(passesTextGates(text), false, `expected pass=false for ${category}`);
  assert(report.findings.some(item => item.category === category && item.severity === 'hard'), `missing hard category ${category}`);
}

function assertSoft(text: string, category: string): void {
  const report = evaluateTextGates(text);
  assert.strictEqual(report.hardBlocked, false, `expected no hard block for ${category}`);
  assert.strictEqual(report.softFlagged, true, `expected soft flag for ${category}`);
  assert.strictEqual(passesTextGates(text), true, `expected pass=true for soft category ${category}`);
  assert(report.findings.some(item => item.category === category && item.severity === 'soft'), `missing soft category ${category}`);
}

const clean = evaluateTextGates('Composed private-room fashion description with clear consent, whole-person framing, and neutral prompt surface.');
assert.strictEqual(clean.format, 'TEXT_METRICS_GATE_CALIBRATION_V1');
assert.strictEqual(clean.hardBlocked, false);
assert.strictEqual(clean.softFlagged, false);
assert.deepStrictEqual(clean.findings, []);
assert.strictEqual(passesTextGates('plain technical description'), true);

assertHard('Reject this because it asks for an explicit procedure with step-by-step sexual framing.', 'explicit_procedure');
assertHard('Reject this because the relation is coercive and non-consensual.', 'agency_harm');
assertHard('Reject this because the subject is age-ambiguous and minor-coded.', 'age_ambiguity');

assertSoft('Review this because it uses fragmented body framing and personhood removed from the scene.', 'use_fragmentation');
assertSoft('Review this because it carries prompt surface contamination through a negative prohibition list.', 'prompt_surface_contamination');

const mixed = evaluateTextGates('This has explicit procedure language plus faceless use and prompt surface contamination.');
assert.strictEqual(mixed.hardBlocked, true);
assert.strictEqual(mixed.softFlagged, true);
assert.deepStrictEqual(categories('explicit procedure with faceless use and prompt surface contamination'), [
  'explicit_procedure',
  'prompt_surface_contamination',
  'use_fragmentation',
]);

console.log('OK text metrics gate calibration');
