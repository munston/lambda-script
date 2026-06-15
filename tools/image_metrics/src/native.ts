declare const require: any;
declare const process: any;
declare const __dirname: string;
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

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

export interface AnalyzeImageRequest { imagePath: string; outDir: string; }

function clamp01(x: number): number { return Number.isFinite(x) ? Math.max(0, Math.min(1, x)) : 0; }
function round6(x: number): number { return Math.round(x * 1000000) / 1000000; }

class Rng {
  private x: number;
  constructor(seed: number) { this.x = seed | 0 || 123456789; }
  u32(): number { let x = this.x | 0; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; this.x = x | 0; return this.x >>> 0; }
  next(): number { return this.u32() / 4294967296; }
}

function hashString(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h >>> 0;
}

function syntheticBytes(id: string, length = 2048): Uint8Array {
  const rng = new Rng(hashString(id));
  const out = new Uint8Array(length);
  const centre = 70 + (rng.u32() % 120);
  for (let i = 0; i < out.length; i++) {
    const wave = 35 * Math.sin(i * 0.031 + (hashString(id) % 97));
    const noise = Math.floor(70 * (rng.next() - 0.5));
    out[i] = Math.max(0, Math.min(255, Math.round(centre + wave + noise)));
  }
  return out;
}

function readBytesOrSynthetic(imagePath: string): Uint8Array {
  if (imagePath.startsWith('synthetic://')) return syntheticBytes(imagePath);
  if (fs.existsSync(imagePath) && fs.statSync(imagePath).isFile()) return new Uint8Array(fs.readFileSync(imagePath));
  return syntheticBytes(`synthetic://${imagePath}`);
}

function resultFromBytes(bytes: Uint8Array): NativeMetricResult {
  const n = Math.max(1, bytes.length);
  let sum = 0, sum2 = 0, grad = 0, block = 0, low = 0, high = 0, even = 0, odd = 0;
  for (let i = 0; i < bytes.length; i++) {
    const v = bytes[i] / 255;
    sum += v; sum2 += v * v;
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
  const lowMass = low / n, highMass = high / n;
  const chromaProxy = Math.abs(even - odd) / Math.max(1, Math.floor(n / 2));
  const lengthNorm = clamp01(Math.log2(n + 1) / 16);
  const surface = clamp01(1 - variance / 0.095);
  const central = clamp01(1 - (0.65 * variance + 0.35 * gradient) / 0.14);
  const compression = clamp01(1 - blockiness / 0.35);
  const background = clamp01(1 - gradient / 0.42);
  const accent = clamp01(0.25 + 0.75 * Math.abs(mean - 0.5) + 0.20 * background);
  const colour = clamp01(0.35 + 1.8 * chromaProxy + 0.25 * highMass);
  const boundary = clamp01(0.15 + gradient / 0.32);
  const upper = clamp01(0.45 + 0.55 * lengthNorm);
  const env = clamp01(0.55 * lowMass + 0.25 * blockiness);
  const chroma = clamp01(1.4 * chromaProxy + 0.15 * highMass);
  const edgePres = clamp01(1 - Math.max(0, 0.16 - gradient) / 0.16);
  const distort = clamp01(Math.max(0, blockiness - 0.18) / 0.32);
  const edgeLoss = clamp01(Math.max(0, 0.10 - gradient) / 0.10);
  const score = 0.14 * surface + 0.16 * central + 0.09 * compression + 0.08 * background + 0.11 * accent + 0.10 * colour + 0.10 * boundary + 0.11 * upper + 0.08 + 0.09 * edgePres - 0.16 * env - 0.18 * chroma - 0.14 * distort - 0.06 * edgeLoss;
  return {
    score: round6(score),
    surface_smoothness: round6(surface),
    central_smoothness: round6(central),
    compression_cleanliness: round6(compression),
    background_softness: round6(background),
    accent_private_energy: round6(accent),
    colour_structure: round6(colour),
    boundary_structure: round6(boundary),
    upper_context_proxy: round6(upper),
    full_frame_context: 1,
    environment_penalty: round6(env),
    chroma_penalty: round6(chroma),
    edge_preservation: round6(edgePres),
    distortion_penalty: round6(distort),
    edge_loss: round6(edgeLoss),
    best_restore_passes: 0
  };
}

function ffiPath(): string {
  const exe = process.platform === 'win32' ? 'image_metrics_ffi.exe' : 'image_metrics_ffi';
  return path.resolve(__dirname, '..', '..', 'bin', exe);
}

function analyzeViaCpp(imagePath: string): NativeMetricResult | null {
  const exe = ffiPath();
  if (!fs.existsSync(exe)) return null;
  const proc = cp.spawnSync(exe, ['analyze', imagePath], { encoding: 'utf-8' });
  if (proc.status !== 0) return null;
  return JSON.parse(proc.stdout).result as NativeMetricResult;
}

export function backendVersion(): string {
  return fs.existsSync(ffiPath()) ? 'cpp-byte-ffi/0.1.1' : 'portable-typescript-byte-shim/0.1.1';
}

export function supportedExtensions(): string {
  return 'C++ byte FFI when built; portable TypeScript byte fallback; synthetic:// fixtures; raw byte files';
}

export function analyzeImageToDir(req: AnalyzeImageRequest): NativeMetricResult {
  fs.mkdirSync(req.outDir, { recursive: true });
  const result = analyzeViaCpp(req.imagePath) || resultFromBytes(readBytesOrSynthetic(req.imagePath));
  fs.writeFileSync(path.join(req.outDir, 'report.json'), JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'feature_fixture.json'), JSON.stringify({ source: req.imagePath, backend: backendVersion(), result }, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'summary.txt'), `backend: ${backendVersion()}\nsource: ${req.imagePath}\nscore: ${result.score.toFixed(6)}\n`);
  return result;
}
