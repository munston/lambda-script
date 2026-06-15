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

export class XorShift32 {
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

export function hash32(a: number, b: number, c: number): number {
  let x = (a | 0) ^ ((b + 0x9e3779b9) | 0) ^ (((c << 6) ^ (c >>> 2)) | 0);
  x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
  return x >>> 0;
}

export function dot(a: number[], b: number[]): number { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; }
export function zeros(n: number): number[] { return Array.from({ length: n }, () => 0); }
export function mean(xs: number[]): number { return xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length); }
export function max(xs: number[]): number { let m = -Infinity; for (const x of xs) if (x > m) m = x; return m; }

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

export function addSparseScaled(target: number[], basis: SparseBasisMask, scale: number): void {
  for (let i = 0; i < basis.indices.length; i++) target[basis.indices[i]] += scale * basis.values[i];
}

export function applyOverlay(baseWeights: number[], basis: SparseBasisMask[], controls: number[]): number[] {
  const out = baseWeights.slice();
  for (let j = 0; j < basis.length; j++) addSparseScaled(out, basis[j], controls[j]);
  return out;
}
