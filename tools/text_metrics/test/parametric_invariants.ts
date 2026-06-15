declare const require: any;
const assert = require('assert');

import { buildSparseBasis, trainParametricMonteCarlo } from '../src';
import type { ParametricSupportConfig, TrainOptions } from '../src';

function approx(a: number, b: number, eps = 1e-9): boolean {
  return Math.abs(a - b) <= eps;
}

function finiteArray(xs: number[]): boolean {
  return xs.every(x => Number.isFinite(x));
}

const config: ParametricSupportConfig = {
  coefficientCount: 48,
  controlCount: 8,
  supportRadius: 3,
  sigma: 1.7,
  seed: 20260615,
  basisAmplitude: 1.0,
  initialScale: 0.06
};

const basis = buildSparseBasis(config);
assert.strictEqual(basis.length, config.controlCount, 'basis count should equal control count');

for (const mask of basis) {
  assert(mask.anchor >= 0 && mask.anchor < config.coefficientCount, 'basis anchor should be in range');
  assert(mask.indices.length > 0, 'basis mask should contain indices');
  assert.strictEqual(mask.indices.length, mask.values.length, 'basis indices/values length mismatch');
  assert(mask.indices.every(i => i >= 0 && i < config.coefficientCount), 'basis index out of range');
  assert(mask.indices.every((value, i, xs) => i === 0 || xs[i - 1] < value), 'basis indices should be strictly increasing');
  assert(finiteArray(mask.values), 'basis values should be finite');
  const norm2 = mask.values.reduce((s, v) => s + v * v, 0);
  assert(approx(norm2, 1.0, 1e-9), `basis mask should be normalised, got norm2=${norm2}`);
}

const repeated = buildSparseBasis(config);
assert.deepStrictEqual(repeated, basis, 'basis construction should be deterministic for identical config');

const changed = buildSparseBasis({ ...config, seed: config.seed + 1 });
assert.notDeepStrictEqual(changed, basis, 'basis construction should respond to seed changes');

const opts: TrainOptions = {
  iterations: 36,
  trainCount: 80,
  valCount: 40,
  thetaLr: 0.16,
  scaleLr: 0.12,
  mcSamples: 6,
  mcWeight: 0.25,
  scalePenalty: 0.010,
  logScaleMin: Math.log(1e-4),
  logScaleMax: Math.log(1.2),
  snapshotEvery: 6
};

const result = trainParametricMonteCarlo(config, opts);
assert.strictEqual(result.config.coefficientCount, config.coefficientCount);
assert.strictEqual(result.config.controlCount, config.controlCount);
assert.strictEqual(result.trainCount, opts.trainCount);
assert.strictEqual(result.valCount, opts.valCount);
assert.strictEqual(result.learnedScales.length, config.controlCount);
assert.strictEqual(result.truthControl.length, config.controlCount);
assert(result.trajectory.length >= 2, 'expected multiple training snapshots');
assert.strictEqual(result.trajectory[result.trajectory.length - 1].iter, opts.iterations - 1, 'last snapshot should be final iteration');
assert(Number.isFinite(result.initialTrainLoss), 'initial train loss should be finite');
assert(Number.isFinite(result.initialValLoss), 'initial validation loss should be finite');
assert(Number.isFinite(result.finalTrainLoss), 'final train loss should be finite');
assert(Number.isFinite(result.finalValLoss), 'final validation loss should be finite');
assert(result.finalTrainAccuracy >= 0 && result.finalTrainAccuracy <= 1, 'train accuracy should be bounded');
assert(result.finalValAccuracy >= 0 && result.finalValAccuracy <= 1, 'validation accuracy should be bounded');
assert(result.learnedScales.every(x => x >= Math.exp(opts.logScaleMin) && x <= Math.exp(opts.logScaleMax)), 'learned scales should respect log-scale bounds');
assert(result.learnedScaleMean > 0, 'learned scale mean should be positive');
assert(result.trajectory.every(row => Number.isFinite(row.trainLoss) && Number.isFinite(row.valLoss)), 'trajectory losses should be finite');
assert(result.trajectory.every(row => row.trainAccuracy >= 0 && row.trainAccuracy <= 1 && row.valAccuracy >= 0 && row.valAccuracy <= 1), 'trajectory accuracies should be bounded');

console.log('OK text metrics parametric invariants');
