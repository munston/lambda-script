declare const require: any;
const fs = require('fs');
const path = require('path');

import { localInterrogationGradientStep } from './mld_local';

export interface SparseBasisMask {
  anchor: number;
  indices: number[];
  values: number[];
}

export interface ParametricSupportConfig {
  coefficientCount: number;
  controlCount: number;
  supportRadius: number;
  sigma: number;
  seed: number;
  basisAmplitude: number;
  initialScale: number;
}

export interface SampledDataset {
  features: number[][];
  labels: number[];
}

export interface IterationSnapshot {
  iter: number;
  trainLoss: number;
  trainAccuracy: number;
  valLoss: number;
  valAccuracy: number;
  meanScale: number;
  maxScale: number;
}

export interface ParametricTrainingResult {
  config: ParametricSupportConfig;
  trainCount: number;
  valCount: number;
  truthControl: number[];
  learnedScales: number[];
  learnedScaleMean: number;
  initialTrainLoss: number;
  initialValLoss: number;
  finalTrainLoss: number;
  finalValLoss: number;
  finalTrainAccuracy: number;
  finalValAccuracy: number;
  trajectory: IterationSnapshot[];
}

class XorShift32 {
  private x: number;
  constructor(seed: number) { this.x = seed | 0 || 123456789; }
  nextU32(): number { let x = this.x | 0; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; this.x = x | 0; return this.x >>> 0; }
  next(): number { return this.nextU32() / 4294967296; }
  normal(): number {
    let u = 0, v = 0;
    while (u <= 1e-12) u = this.next();
    while (v <= 1e-12) v = this.next();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
}

function hash32(a: number, b: number, c: number): number {
  let x = (a | 0) ^ ((b + 0x9e3779b9) | 0) ^ (((c << 6) ^ (c >>> 2)) | 0);
  x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
  return x >>> 0;
}

function sigmoid(x: number): number { return x >= 0 ? 1 / (1 + Math.exp(-x)) : Math.exp(x) / (1 + Math.exp(x)); }
function dot(a: number[], b: number[]): number { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; }
function zeros(n: number): number[] { return Array.from({ length: n }, () => 0); }
function mean(xs: number[]): number { return xs.reduce((a, b) => a + b, 0) / xs.length; }
function max(xs: number[]): number { let m = -Infinity; for (const x of xs) if (x > m) m = x; return m; }

export function buildSparseBasis(config: ParametricSupportConfig): SparseBasisMask[] {
  const out: SparseBasisMask[] = [];
  const n = config.coefficientCount;
  const m = config.controlCount;
  const gap = Math.max(1, Math.floor(n / m));
  for (let j = 0; j < m; j++) {
    const anchorJitter = (hash32(config.seed, j, 11) % Math.max(1, Math.floor(gap / 2))) - Math.floor(gap / 4);
    const anchor = Math.max(0, Math.min(n - 1, j * gap + Math.floor(gap / 2) + anchorJitter));
    const indices: number[] = [];
    const values: number[] = [];
    let norm2 = 0;
    for (let k = Math.max(0, anchor - config.supportRadius); k <= Math.min(n - 1, anchor + config.supportRadius); k++) {
      const dist = (k - anchor) / config.sigma;
      const kernel = Math.exp(-0.5 * dist * dist);
      const rng = new XorShift32(hash32(config.seed, j, k));
      const coeff = kernel * rng.normal() * config.basisAmplitude;
      indices.push(k);
      values.push(coeff);
      norm2 += coeff * coeff;
    }
    const norm = Math.sqrt(Math.max(1e-12, norm2));
    for (let i = 0; i < values.length; i++) values[i] /= norm;
    out.push({ anchor, indices, values });
  }
  return out;
}

function addSparseScaled(target: number[], basis: SparseBasisMask, scale: number): void {
  for (let i = 0; i < basis.indices.length; i++) target[basis.indices[i]] += scale * basis.values[i];
}

function sparseDot(basis: SparseBasisMask, dense: number[]): number {
  let s = 0;
  for (let i = 0; i < basis.indices.length; i++) s += basis.values[i] * dense[basis.indices[i]];
  return s;
}

function makeTrueWeights(config: ParametricSupportConfig, basis: SparseBasisMask[]): { truthControl: number[]; weights: number[] } {
  const rng = new XorShift32(hash32(config.seed, 991, 17));
  const truthControl = Array.from({ length: config.controlCount }, (_, j) => (j % 3 === 0 || j % 5 === 0) ? 0.42 * rng.normal() : 0.0);
  const weights = zeros(config.coefficientCount);
  for (let j = 0; j < basis.length; j++) addSparseScaled(weights, basis[j], truthControl[j]);
  return { truthControl, weights };
}

function makeDataset(count: number, weights: number[], seed: number): SampledDataset {
  const rng = new XorShift32(seed);
  const features: number[][] = [];
  const labels: number[] = [];
  const n = weights.length;
  for (let i = 0; i < count; i++) {
    const x = Array.from({ length: n }, () => rng.normal());
    const logit = dot(weights, x) + 0.45 * rng.normal();
    features.push(x);
    labels.push(logit >= 0 ? 1 : -1);
  }
  return { features, labels };
}

function logisticStats(data: SampledDataset, weights: number[]): { loss: number; accuracy: number; grad: number[] } {
  const grad = zeros(weights.length);
  let loss = 0, correct = 0;
  for (let i = 0; i < data.features.length; i++) {
    const x = data.features[i];
    const y = data.labels[i];
    const yz = y * dot(weights, x);
    loss += Math.log1p(Math.exp(-yz));
    if (yz > 0) correct++;
    const coeff = -y / (1 + Math.exp(yz));
    for (let k = 0; k < grad.length; k++) grad[k] += coeff * x[k];
  }
  const inv = 1 / data.features.length;
  for (let k = 0; k < grad.length; k++) grad[k] *= inv;
  return { loss: loss * inv, accuracy: correct * inv, grad };
}

function applyOverlay(baseWeights: number[], basis: SparseBasisMask[], controls: number[]): number[] {
  const out = baseWeights.slice();
  for (let j = 0; j < basis.length; j++) addSparseScaled(out, basis[j], controls[j]);
  return out;
}

export interface TrainOptions {
  iterations: number;
  trainCount: number;
  valCount: number;
  thetaLr: number;
  scaleLr: number;
  mcSamples: number;
  mcWeight: number;
  scalePenalty: number;
  logScaleMin: number;
  logScaleMax: number;
  snapshotEvery: number;
}

export function trainParametricMonteCarlo(config: ParametricSupportConfig, opts: TrainOptions): ParametricTrainingResult {
  const basis = buildSparseBasis(config);
  const truth = makeTrueWeights(config, basis);
  const train = makeDataset(opts.trainCount, truth.weights, hash32(config.seed, 123, 1));
  const val = makeDataset(opts.valCount, truth.weights, hash32(config.seed, 123, 2));
  const theta = zeros(config.coefficientCount);
  const logScales = Array.from({ length: config.controlCount }, () => Math.log(config.initialScale));
  const initialTrain = logisticStats(train, theta);
  const initialVal = logisticStats(val, theta);
  const trajectory: IterationSnapshot[] = [];
  const rng = new XorShift32(hash32(config.seed, 444, 9));

  for (let iter = 0; iter < opts.iterations; iter++) {
    const trainStats = logisticStats(train, theta);
    const gradTheta = trainStats.grad.map(v => -v);
    const gradLogScale = zeros(config.controlCount);
    const mcThetaAccum = zeros(config.coefficientCount);
    const rewards: number[] = [];
    const zs: number[][] = [];
    for (let s = 0; s < opts.mcSamples; s++) {
      const z = Array.from({ length: config.controlCount }, () => rng.normal());
      const controls = z.map((v, j) => Math.exp(logScales[j]) * v);
      const perturbed = applyOverlay(theta, basis, controls);
      const valStats = logisticStats(val, perturbed);
      const rewardGrad = valStats.grad.map(v => -v);
      const reward = -valStats.loss;
      rewards.push(reward);
      zs.push(z);
      for (let k = 0; k < mcThetaAccum.length; k++) mcThetaAccum[k] += rewardGrad[k];
    }
    const invMc = 1 / opts.mcSamples;
    for (let k = 0; k < theta.length; k++) theta[k] += opts.thetaLr * (gradTheta[k] + opts.mcWeight * mcThetaAccum[k] * invMc);
    const probeZs = zs;
    const scaleObjective = (candidateLogScales: number[]): number => {
      let acc = 0;
      for (const z of probeZs) {
        const controls = z.map((v, j) => Math.exp(candidateLogScales[j]) * v);
        const perturbed = applyOverlay(theta, basis, controls);
        acc += -logisticStats(val, perturbed).loss;
      }
      const scalePenalty = candidateLogScales.map(Math.exp).reduce((s, x) => s + x * x, 0) / candidateLogScales.length;
      return acc / Math.max(1, probeZs.length) - opts.scalePenalty * scalePenalty;
    };
    const stepped = localInterrogationGradientStep(logScales, scaleObjective, {
      seed: config.seed ^ (iter * 2654435761),
      stepSize: 0.035,
      steps: Math.max(1, Math.ceil(Math.sqrt(logScales.length))),
      lower: opts.logScaleMin,
      upper: opts.logScaleMax,
      maximize: true
    }, opts.scaleLr);
    for (let j = 0; j < logScales.length; j++) logScales[j] = stepped.next[j];
    if (iter % opts.snapshotEvery === 0 || iter === opts.iterations - 1) {
      const scalesNow = logScales.map(Math.exp);
      const valProbe = logisticStats(val, theta);
      trajectory.push({
        iter,
        trainLoss: trainStats.loss,
        trainAccuracy: trainStats.accuracy,
        valLoss: valProbe.loss,
        valAccuracy: valProbe.accuracy,
        meanScale: mean(scalesNow),
        maxScale: max(scalesNow)
      });
    }
  }

  const finalTrain = logisticStats(train, theta);
  const finalVal = logisticStats(val, theta);
  const learnedScales = logScales.map(Math.exp);
  return {
    config,
    trainCount: opts.trainCount,
    valCount: opts.valCount,
    truthControl: truth.truthControl,
    learnedScales,
    learnedScaleMean: mean(learnedScales),
    initialTrainLoss: initialTrain.loss,
    initialValLoss: initialVal.loss,
    finalTrainLoss: finalTrain.loss,
    finalValLoss: finalVal.loss,
    finalTrainAccuracy: finalTrain.accuracy,
    finalValAccuracy: finalVal.accuracy,
    trajectory
  };
}

export function defaultParametricDemo(outDir?: string): ParametricTrainingResult {
  const config: ParametricSupportConfig = {
    coefficientCount: 160,
    controlCount: 20,
    supportRadius: 7,
    sigma: 3.0,
    seed: 20260614,
    basisAmplitude: 1.0,
    initialScale: 0.08
  };
  const opts: TrainOptions = {
    iterations: 260,
    trainCount: 260,
    valCount: 140,
    thetaLr: 0.18,
    scaleLr: 0.18,
    mcSamples: 18,
    mcWeight: 0.35,
    scalePenalty: 0.010,
    logScaleMin: Math.log(1e-4),
    logScaleMax: Math.log(1.75),
    snapshotEvery: 10
  };
  const result = trainParametricMonteCarlo(config, opts);
  if (outDir) {
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(path.join(outDir, 'parametric_demo_report.json'), JSON.stringify(result, null, 2));
    const lines = [
      `initial_train_loss: ${result.initialTrainLoss.toFixed(6)}`,
      `initial_val_loss: ${result.initialValLoss.toFixed(6)}`,
      `final_train_loss: ${result.finalTrainLoss.toFixed(6)}`,
      `final_val_loss: ${result.finalValLoss.toFixed(6)}`,
      `final_train_accuracy: ${result.finalTrainAccuracy.toFixed(6)}`,
      `final_val_accuracy: ${result.finalValAccuracy.toFixed(6)}`,
      `learned_scale_mean: ${result.learnedScaleMean.toFixed(6)}`
    ];
    fs.writeFileSync(path.join(outDir, 'parametric_demo_summary.txt'), lines.join('\n') + '\n');
  }
  return result;
}
