declare const require: any;
const fs = require('fs');
const path = require('path');

import { analyzeImageToDir } from './native';
import { applyOverlay, buildSparseBasis, dot, hash32, max, mean, XorShift32, zeros } from './parametric';
import type { IterationSnapshot, ParametricSupportConfig, SampledDataset } from './parametric';

export interface ImageFeatureRecord {
  imagePath: string;
  nativeScore: number;
  label: number;
  rawFeatures: number[];
  normalizedFeatures: number[];
}

export interface ImageParametricTrainingResult {
  featureNames: string[];
  imagePaths: string[];
  nativeScores: number[];
  nativeScoreThreshold: number;
  trainImageCount: number;
  valImageCount: number;
  trainSampleCount: number;
  valSampleCount: number;
  learnedScales: number[];
  learnedScaleMean: number;
  initialTrainLoss: number;
  initialValLoss: number;
  finalTrainLoss: number;
  finalValLoss: number;
  finalTrainAccuracy: number;
  finalValAccuracy: number;
  finalValScoreCorrelation: number;
  trajectory: IterationSnapshot[];
  backend: string;
}

const FEATURE_NAMES = [
  'surface_smoothness',
  'central_smoothness',
  'compression_cleanliness',
  'background_softness',
  'accent_private_energy',
  'colour_structure',
  'boundary_structure',
  'upper_context_proxy',
  'full_frame_context',
  'environment_penalty',
  'chroma_penalty',
  'edge_preservation',
  'distortion_penalty',
  'edge_loss'
];

function logisticStats(data: SampledDataset, weights: number[]): { loss: number; accuracy: number; grad: number[]; logits: number[] } {
  const grad = zeros(weights.length);
  let loss = 0, correct = 0;
  const logits: number[] = [];
  for (let i = 0; i < data.features.length; i++) {
    const x = data.features[i], y = data.labels[i], z = dot(weights, x), yz = y * z;
    logits.push(z);
    loss += Math.log1p(Math.exp(-Math.max(-60, Math.min(60, yz))));
    if (yz > 0) correct++;
    const coeff = -y / (1 + Math.exp(Math.max(-60, Math.min(60, yz))));
    for (let k = 0; k < grad.length; k++) grad[k] += coeff * x[k];
  }
  const inv = 1 / Math.max(1, data.features.length);
  for (let k = 0; k < grad.length; k++) grad[k] *= inv;
  return { loss: loss * inv, accuracy: correct * inv, grad, logits };
}

function median(xs: number[]): number {
  const ys = xs.slice().sort((a, b) => a - b);
  const k = Math.floor(ys.length / 2);
  return ys.length % 2 ? ys[k] : 0.5 * (ys[k - 1] + ys[k]);
}

function corr(a: number[], b: number[]): number {
  const ma = mean(a), mb = mean(b);
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < a.length; i++) {
    const xa = a[i] - ma, xb = b[i] - mb;
    num += xa * xb; da += xa * xa; db += xb * xb;
  }
  return num / Math.sqrt(Math.max(1e-12, da * db));
}

function featureVectorFromReport(report: any): number[] {
  return FEATURE_NAMES.map(name => Number(report[name] ?? 0));
}

function standardize(records: { rawFeatures: number[] }[]): number[][] {
  const d = records[0].rawFeatures.length;
  const means = zeros(d), vars = zeros(d);
  for (const r of records) for (let j = 0; j < d; j++) means[j] += r.rawFeatures[j];
  for (let j = 0; j < d; j++) means[j] /= records.length;
  for (const r of records) for (let j = 0; j < d; j++) vars[j] += Math.pow(r.rawFeatures[j] - means[j], 2);
  const stds = vars.map(v => Math.sqrt(v / records.length + 1e-6));
  return records.map(r => r.rawFeatures.map((v, j) => (v - means[j]) / stds[j]));
}

function makeSyntheticPaths(count: number): string[] {
  return Array.from({ length: count }, (_, i) => `synthetic://portable-image-${String(i).padStart(2, '0')}`);
}

function prepareRecords(imagePaths: string[], outDir: string): ImageFeatureRecord[] {
  const rawRecords: Omit<ImageFeatureRecord, 'label' | 'normalizedFeatures'>[] = [];
  for (let i = 0; i < imagePaths.length; i++) {
    const analysisDir = path.join(outDir, `analysis_${String(i).padStart(2, '0')}`);
    const report = analyzeImageToDir({ imagePath: imagePaths[i], outDir: analysisDir });
    rawRecords.push({ imagePath: imagePaths[i], nativeScore: Number(report.score), rawFeatures: featureVectorFromReport(report) });
  }
  while (rawRecords.length < 8) {
    const source = rawRecords[rawRecords.length % Math.max(1, rawRecords.length)] || { imagePath: 'synthetic://seed', nativeScore: 0, rawFeatures: zeros(FEATURE_NAMES.length) };
    const rng = new XorShift32(hash32(20260615, rawRecords.length, 42));
    rawRecords.push({
      imagePath: `${source.imagePath}::feature-jitter-${rawRecords.length}`,
      nativeScore: source.nativeScore + 0.01 * rng.normal(),
      rawFeatures: source.rawFeatures.map(v => v + 0.035 * rng.normal())
    });
  }
  const threshold = median(rawRecords.map(r => r.nativeScore));
  const normalized = standardize(rawRecords);
  return rawRecords.map((r, i) => ({
    imagePath: r.imagePath,
    nativeScore: r.nativeScore,
    label: r.nativeScore >= threshold ? 1 : -1,
    rawFeatures: r.rawFeatures,
    normalizedFeatures: normalized[i]
  }));
}

function buildAugmentedDataset(records: ImageFeatureRecord[], seed: number, repeats: number, noiseStd: number): SampledDataset {
  const rng = new XorShift32(seed);
  const features: number[][] = [];
  const labels: number[] = [];
  for (const r of records) {
    features.push(r.normalizedFeatures.slice());
    labels.push(r.label);
    for (let rep = 0; rep < repeats; rep++) {
      features.push(r.normalizedFeatures.map(v => v + noiseStd * rng.normal()));
      labels.push(r.label);
    }
  }
  return { features, labels };
}

function trainImageClassifier(trainRecords: ImageFeatureRecord[], valRecords: ImageFeatureRecord[], config: ParametricSupportConfig): ImageParametricTrainingResult {
  const basis = buildSparseBasis(config);
  const train = buildAugmentedDataset(trainRecords, config.seed ^ 0x55aa, 16, 0.05);
  const val: SampledDataset = { features: valRecords.map(r => r.normalizedFeatures), labels: valRecords.map(r => r.label) };
  const theta = zeros(config.coefficientCount);
  const logScales = Array.from({ length: config.controlCount }, () => Math.log(config.initialScale));
  const initialTrain = logisticStats(train, theta);
  const initialVal = logisticStats(val, theta);
  const trajectory: IterationSnapshot[] = [];
  const rng = new XorShift32(config.seed ^ 0x0f0f0f);

  for (let iter = 0; iter < 120; iter++) {
    const trainStats = logisticStats(train, theta);
    const gradTheta = trainStats.grad.map(v => -v);
    const mcThetaAccum = zeros(config.coefficientCount);
    const zs: number[][] = [];
    for (let s = 0; s < 12; s++) {
      const z = Array.from({ length: config.controlCount }, () => rng.normal());
      const controls = z.map((v, j) => Math.exp(logScales[j]) * v);
      const valStats = logisticStats(val, applyOverlay(theta, basis, controls));
      for (let k = 0; k < mcThetaAccum.length; k++) mcThetaAccum[k] += -valStats.grad[k];
      zs.push(z);
    }
    for (let k = 0; k < theta.length; k++) theta[k] += 0.20 * (gradTheta[k] + 0.25 * mcThetaAccum[k] / Math.max(1, zs.length));
    for (let j = 0; j < logScales.length; j++) {
      let best = logScales[j], bestObj = -Infinity;
      for (const delta of [-0.035, 0, 0.035]) {
        const candidate = logScales.slice();
        candidate[j] = Math.max(Math.log(1e-4), Math.min(Math.log(1.5), candidate[j] + delta));
        let acc = 0;
        for (const z of zs) {
          const controls = z.map((v, q) => Math.exp(candidate[q]) * v);
          acc += -logisticStats(val, applyOverlay(theta, basis, controls)).loss;
        }
        const penalty = candidate.map(Math.exp).reduce((s, x) => s + x * x, 0) / candidate.length;
        const obj = acc / Math.max(1, zs.length) - 0.010 * penalty;
        if (obj > bestObj) { bestObj = obj; best = candidate[j]; }
      }
      logScales[j] = 0.88 * logScales[j] + 0.12 * best;
    }
    if (iter % 10 === 0 || iter === 119) {
      const scalesNow = logScales.map(Math.exp);
      const valProbe = logisticStats(val, theta);
      trajectory.push({ iter, trainLoss: trainStats.loss, trainAccuracy: trainStats.accuracy, valLoss: valProbe.loss, valAccuracy: valProbe.accuracy, meanScale: mean(scalesNow), maxScale: max(scalesNow) });
    }
  }

  const finalTrain = logisticStats(train, theta);
  const finalVal = logisticStats(val, theta);
  const learnedScales = logScales.map(Math.exp);
  const logits = valRecords.map(r => dot(theta, r.normalizedFeatures));
  const scores = valRecords.map(r => r.nativeScore);
  const allRecords = trainRecords.concat(valRecords);
  return {
    featureNames: FEATURE_NAMES,
    imagePaths: allRecords.map(r => r.imagePath),
    nativeScores: allRecords.map(r => r.nativeScore),
    nativeScoreThreshold: median(allRecords.map(r => r.nativeScore)),
    trainImageCount: trainRecords.length,
    valImageCount: valRecords.length,
    trainSampleCount: train.features.length,
    valSampleCount: val.features.length,
    learnedScales,
    learnedScaleMean: mean(learnedScales),
    initialTrainLoss: initialTrain.loss,
    initialValLoss: initialVal.loss,
    finalTrainLoss: finalTrain.loss,
    finalValLoss: finalVal.loss,
    finalTrainAccuracy: finalTrain.accuracy,
    finalValAccuracy: finalVal.accuracy,
    finalValScoreCorrelation: corr(logits, scores),
    trajectory,
    backend: 'typescript+c++-ffi'
  };
}

export function defaultImageParametricDemo(outDir = 'runs/image-parametric-demo', imagePaths?: string[]): ImageParametricTrainingResult {
  fs.mkdirSync(outDir, { recursive: true });
  const paths = imagePaths && imagePaths.length > 0 ? imagePaths : makeSyntheticPaths(12);
  const records = prepareRecords(paths, outDir);
  const valCount = Math.max(2, Math.floor(records.length * 0.3));
  const trainRecords = records.slice(0, records.length - valCount);
  const valRecords = records.slice(records.length - valCount);
  const config: ParametricSupportConfig = {
    coefficientCount: FEATURE_NAMES.length,
    controlCount: Math.min(8, FEATURE_NAMES.length),
    supportRadius: 2,
    sigma: 1.1,
    seed: 20260615,
    basisAmplitude: 1.0,
    initialScale: 0.08
  };
  const result = trainImageClassifier(trainRecords, valRecords, config);
  fs.writeFileSync(path.join(outDir, 'image_parametric_report.json'), JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(outDir, 'image_parametric_summary.txt'), [
    `backend: ${result.backend}`,
    `native_score_threshold: ${result.nativeScoreThreshold.toFixed(6)}`,
    `initial_train_loss: ${result.initialTrainLoss.toFixed(6)}`,
    `initial_val_loss: ${result.initialValLoss.toFixed(6)}`,
    `final_train_loss: ${result.finalTrainLoss.toFixed(6)}`,
    `final_val_loss: ${result.finalValLoss.toFixed(6)}`,
    `final_train_accuracy: ${result.finalTrainAccuracy.toFixed(6)}`,
    `final_val_accuracy: ${result.finalValAccuracy.toFixed(6)}`,
    `final_val_score_correlation: ${result.finalValScoreCorrelation.toFixed(6)}`,
    `learned_scale_mean: ${result.learnedScaleMean.toFixed(6)}`
  ].join('\n') + '\n');
  return result;
}
