declare const require: any;
const fs = require('fs');
const path = require('path');

export interface NativeMetricResult {
  score: number;
  surface_smoothness: number;
  central_smoothness: number;
  compression_cleanliness: number;
  background_softness: number;
  accent_private_energy: number;
  colour_structure: number;
  boundary_structure: number;
  upper_context_proxy: number;
  full_frame_context: number;
  environment_penalty: number;
  chroma_penalty: number;
  edge_preservation: number;
  distortion_penalty: number;
  edge_loss: number;
  best_restore_passes: number;
}

export interface RgbFrameU8 {
  width: number;
  height: number;
  channels: number;
  data: Uint8Array;
}

export interface AnalyzeImageRequest {
  imagePath: string;
  outDir: string;
}

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

function round6(x: number): number {
  return Math.round(x * 1_000_000) / 1_000_000;
}

function hashString(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

class XorShift32 {
  private x: number;
  constructor(seed: number) { this.x = seed | 0 || 123456789; }
  nextU32(): number { let x = this.x | 0; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; this.x = x | 0; return this.x >>> 0; }
  next(): number { return this.nextU32() / 4294967296; }
}

function bytesFromSyntheticId(id: string, length = 2048): Uint8Array {
  const rng = new XorShift32(hashString(id));
  const out = new Uint8Array(length);
  const centre = 70 + (rng.nextU32() % 120);
  for (let i = 0; i < out.length; i++) {
    const wave = 35 * Math.sin(i * 0.031 + (hashString(id) % 97));
    const noise = Math.floor(70 * (rng.next() - 0.5));
    out[i] = Math.max(0, Math.min(255, Math.round(centre + wave + noise)));
  }
  return out;
}

function readBytesOrSynthetic(imagePath: string): Uint8Array {
  if (imagePath.startsWith('synthetic://')) return bytesFromSyntheticId(imagePath);
  if (fs.existsSync(imagePath) && fs.statSync(imagePath).isFile()) {
    return new Uint8Array(fs.readFileSync(imagePath));
  }
  return bytesFromSyntheticId(`synthetic://${imagePath}`);
}

function byteStats(bytes: Uint8Array): {
  mean: number;
  variance: number;
  gradient: number;
  blockiness: number;
  lowMass: number;
  highMass: number;
  chromaProxy: number;
  lengthNorm: number;
} {
  const n = Math.max(1, bytes.length);
  let sum = 0, sum2 = 0, grad = 0, block = 0, low = 0, high = 0, even = 0, odd = 0;
  for (let i = 0; i < bytes.length; i++) {
    const v = bytes[i] / 255;
    sum += v;
    sum2 += v * v;
    if (i > 0) grad += Math.abs(bytes[i] - bytes[i - 1]) / 255;
    if (i > 0 && i % 8 === 0) block += Math.abs(bytes[i] - bytes[i - 1]) / 255;
    if (v < 0.22) low++;
    if (v > 0.78) high++;
    if (i % 2 === 0) even += v; else odd += v;
  }
  const mean = sum / n;
  const variance = Math.max(0, sum2 / n - mean * mean);
  const gradient = grad / Math.max(1, n - 1);
  const blockiness = block / Math.max(1, Math.floor(n / 8));
  const chromaProxy = Math.abs(even - odd) / Math.max(1, Math.floor(n / 2));
  return {
    mean,
    variance,
    gradient,
    blockiness,
    lowMass: low / n,
    highMass: high / n,
    chromaProxy,
    lengthNorm: clamp01(Math.log2(n + 1) / 16)
  };
}

function resultFromStats(s: ReturnType<typeof byteStats>): NativeMetricResult {
  const surface_smoothness = clamp01(1 - s.variance / 0.095);
  const central_smoothness = clamp01(1 - (0.65 * s.variance + 0.35 * s.gradient) / 0.14);
  const compression_cleanliness = clamp01(1 - s.blockiness / 0.35);
  const background_softness = clamp01(1 - s.gradient / 0.42);
  const accent_private_energy = clamp01(0.25 + 0.75 * Math.abs(s.mean - 0.5) + 0.20 * background_softness);
  const colour_structure = clamp01(0.35 + 1.8 * s.chromaProxy + 0.25 * s.highMass);
  const boundary_structure = clamp01(0.15 + s.gradient / 0.32);
  const upper_context_proxy = clamp01(0.45 + 0.55 * s.lengthNorm);
  const full_frame_context = 1.0;
  const environment_penalty = clamp01(0.55 * s.lowMass + 0.25 * s.blockiness);
  const chroma_penalty = clamp01(1.4 * s.chromaProxy + 0.15 * s.highMass);
  const edge_preservation = clamp01(1 - Math.max(0, 0.16 - s.gradient) / 0.16);
  const distortion_penalty = clamp01(Math.max(0, s.blockiness - 0.18) / 0.32);
  const edge_loss = clamp01(Math.max(0, 0.10 - s.gradient) / 0.10);
  const score = (
    0.14 * surface_smoothness +
    0.16 * central_smoothness +
    0.09 * compression_cleanliness +
    0.08 * background_softness +
    0.11 * accent_private_energy +
    0.10 * colour_structure +
    0.10 * boundary_structure +
    0.11 * upper_context_proxy +
    0.08 * full_frame_context +
    0.09 * edge_preservation -
    0.16 * environment_penalty -
    0.18 * chroma_penalty -
    0.14 * distortion_penalty -
    0.06 * edge_loss
  );
  return {
    score: round6(score),
    surface_smoothness: round6(surface_smoothness),
    central_smoothness: round6(central_smoothness),
    compression_cleanliness: round6(compression_cleanliness),
    background_softness: round6(background_softness),
    accent_private_energy: round6(accent_private_energy),
    colour_structure: round6(colour_structure),
    boundary_structure: round6(boundary_structure),
    upper_context_proxy: round6(upper_context_proxy),
    full_frame_context: round6(full_frame_context),
    environment_penalty: round6(environment_penalty),
    chroma_penalty: round6(chroma_penalty),
    edge_preservation: round6(edge_preservation),
    distortion_penalty: round6(distortion_penalty),
    edge_loss: round6(edge_loss),
    best_restore_passes: 0
  };
}

export function backendVersion(): string {
  return 'portable-typescript-shim/0.2.0';
}

export function supportedExtensions(): string {
  return 'portable shim: synthetic://, byte-buffer files, JSON feature fixtures';
}

export function analyzeRgbU8(frame: RgbFrameU8): NativeMetricResult {
  const expected = Math.max(0, frame.width * frame.height * Math.max(1, frame.channels));
  const data = expected > 0 && frame.data.length >= expected ? frame.data.slice(0, expected) : frame.data;
  return resultFromStats(byteStats(data));
}

export function analyzeImageToDir(req: AnalyzeImageRequest): NativeMetricResult {
  fs.mkdirSync(req.outDir, { recursive: true });
  const bytes = readBytesOrSynthetic(req.imagePath);
  const result = resultFromStats(byteStats(bytes));
  const reportPath = path.join(req.outDir, 'report.json');
  const summaryPath = path.join(req.outDir, 'summary.txt');
  const fixturePath = path.join(req.outDir, 'feature_fixture.json');
  fs.writeFileSync(reportPath, JSON.stringify(result, null, 2));
  fs.writeFileSync(fixturePath, JSON.stringify({
    source: req.imagePath,
    backend: backendVersion(),
    byteLength: bytes.length,
    stats: byteStats(bytes),
    result
  }, null, 2));
  fs.writeFileSync(summaryPath, [
    `backend: ${backendVersion()}`,
    `source: ${req.imagePath}`,
    `score: ${result.score.toFixed(6)}`,
    `surface_smoothness: ${result.surface_smoothness.toFixed(6)}`,
    `central_smoothness: ${result.central_smoothness.toFixed(6)}`,
    `compression_cleanliness: ${result.compression_cleanliness.toFixed(6)}`,
    `background_softness: ${result.background_softness.toFixed(6)}`,
    `accent_private_energy: ${result.accent_private_energy.toFixed(6)}`,
    `colour_structure: ${result.colour_structure.toFixed(6)}`,
    `boundary_structure: ${result.boundary_structure.toFixed(6)}`
  ].join('\n') + '\n');
  return result;
}

export function restoreImageToDir(req: AnalyzeImageRequest): NativeMetricResult {
  const result = analyzeImageToDir(req);
  result.best_restore_passes = 0;
  fs.writeFileSync(path.join(req.outDir, 'restore_note.txt'), 'portable shim: restore is a no-op placeholder\n');
  fs.writeFileSync(path.join(req.outDir, 'report.json'), JSON.stringify(result, null, 2));
  return result;
}
