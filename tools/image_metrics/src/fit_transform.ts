declare const require: any;
declare const Buffer: any;
const fs = require('fs');
const path = require('path');

interface Frame { w: number; h: number; rgb: Float64Array; }
interface FitParams { strength: number; deepMix: number; waveGain: number; gradGain: number; redGain: number; greenGain: number; blueGain: number; smoothBlend: number; }
export interface FitTransformRequest { sourcePath: string; targetPath: string; outDir: string; seed: number; trials: number; smoothnessWeight: number; edgeWeight: number; complexityWeight: number; }
export interface FitTransformResult { mode: string; source: string; target: string; width: number; height: number; seed: number; trials: number; bestLoss: number; reconstructionLoss: number; regularizationLoss: number; bestParams: FitParams; outputs: string[]; }

class Rng {
  private x: number;
  constructor(seed: number) { this.x = seed | 0 || 123456789; }
  u32(): number { let x = this.x | 0; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; this.x = x | 0; return this.x >>> 0; }
  next(): number { return this.u32() / 4294967296; }
  normal(): number { let u = 0, v = 0; while (u <= 1e-12) u = this.next(); while (v <= 1e-12) v = this.next(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
}
function clamp01(x: number): number { return Number.isFinite(x) ? Math.max(0, Math.min(1, x)) : 0; }
function clampByte(x: number): number { return Math.max(0, Math.min(255, Math.round(clamp01(x) * 255))); }
function px(w: number, x: number, y: number): number { return y * w + x; }
function frameIndex(f: Frame, x: number, y: number, c: number): number { return ((y * f.w + x) * 3) + c; }
function cloneParams(p: FitParams): FitParams { return { strength: p.strength, deepMix: p.deepMix, waveGain: p.waveGain, gradGain: p.gradGain, redGain: p.redGain, greenGain: p.greenGain, blueGain: p.blueGain, smoothBlend: p.smoothBlend }; }
function bounded(x: number, lo: number, hi: number): number { return Math.max(lo, Math.min(hi, x)); }

function readTokens(buf: any): { tokens: string[]; offset: number } {
  const tokens: string[] = [];
  let i = 0;
  while (i < buf.length && tokens.length < 4) {
    while (i < buf.length && buf[i] <= 32) i++;
    if (buf[i] === 35) { while (i < buf.length && buf[i] !== 10) i++; continue; }
    let s = '';
    while (i < buf.length && buf[i] > 32) { s += String.fromCharCode(buf[i]); i++; }
    if (s) tokens.push(s);
  }
  while (i < buf.length && buf[i] <= 32) i++;
  return { tokens, offset: i };
}
function readPpm(file: string): Frame {
  const buf = fs.readFileSync(file);
  const parsed = readTokens(buf);
  const tokens = parsed.tokens;
  if (tokens[0] !== 'P6') throw new Error('PPM reader only supports P6');
  const w = Number(tokens[1]), h = Number(tokens[2]), maxv = Number(tokens[3]);
  if (!w || !h || !maxv) throw new Error('invalid PPM header');
  const rgb = new Float64Array(w * h * 3);
  for (let i = 0; i < rgb.length; i++) rgb[i] = Number(buf[parsed.offset + i] || 0) / maxv;
  return { w, h, rgb };
}
function readBmp(file: string): Frame {
  const buf = fs.readFileSync(file);
  if (buf[0] !== 0x42 || buf[1] !== 0x4d) throw new Error('invalid BMP header');
  const off = buf.readUInt32LE(10);
  const w = buf.readInt32LE(18);
  const rawH = buf.readInt32LE(22);
  const h = Math.abs(rawH);
  const bpp = buf.readUInt16LE(28);
  if (bpp !== 24) throw new Error('BMP reader only supports 24-bit BMP');
  const row = Math.floor((w * 3 + 3) / 4) * 4;
  const rgb = new Float64Array(w * h * 3);
  for (let y = 0; y < h; y++) {
    const sy = rawH > 0 ? h - 1 - y : y;
    for (let x = 0; x < w; x++) {
      const src = off + sy * row + x * 3;
      const dst = (y * w + x) * 3;
      rgb[dst + 0] = Number(buf[src + 2]) / 255;
      rgb[dst + 1] = Number(buf[src + 1]) / 255;
      rgb[dst + 2] = Number(buf[src + 0]) / 255;
    }
  }
  return { w, h, rgb };
}
function syntheticFrame(id: string, w = 192, h = 192): Frame {
  let hash = 2166136261 >>> 0;
  for (let i = 0; i < id.length; i++) { hash ^= id.charCodeAt(i); hash = Math.imul(hash, 16777619) >>> 0; }
  const rng = new Rng(hash | 0);
  const rgb = new Float64Array(w * h * 3);
  const phase = (hash % 1000) / 1000;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const nx = x / Math.max(1, w - 1), ny = y / Math.max(1, h - 1);
    const base = 0.42 + 0.28 * nx + 0.15 * Math.sin(2 * Math.PI * (nx * 2.3 + ny * 1.7 + phase));
    const centre = Math.exp(-(((nx - 0.52) ** 2) / 0.055 + ((ny - 0.46) ** 2) / 0.080));
    const dark = Math.exp(-(((nx - 0.76) ** 2) / 0.020 + ((ny - 0.55) ** 2) / 0.060));
    const p = (y * w + x) * 3;
    rgb[p + 0] = clamp01(base + 0.18 * centre - 0.20 * dark + 0.025 * rng.normal());
    rgb[p + 1] = clamp01(base + 0.12 * centre - 0.18 * dark + 0.025 * rng.normal());
    rgb[p + 2] = clamp01(base + 0.08 * centre - 0.14 * dark + 0.025 * rng.normal());
  }
  return { w, h, rgb };
}
function readFrame(imagePath: string): Frame {
  if (imagePath.startsWith('synthetic://')) return syntheticFrame(imagePath);
  const ext = path.extname(imagePath).toLowerCase();
  if (ext === '.ppm') return readPpm(imagePath);
  if (ext === '.bmp') return readBmp(imagePath);
  throw new Error('fit-transform supports synthetic://, .ppm, and 24-bit .bmp inputs');
}
function writePpm(file: string, f: Frame): void {
  const header = Buffer.from(`P6\n${f.w} ${f.h}\n255\n`, 'ascii');
  const body = Buffer.alloc(f.w * f.h * 3);
  for (let i = 0; i < body.length; i++) body[i] = clampByte(f.rgb[i]);
  fs.writeFileSync(file, Buffer.concat([header, body]));
}
function writeBmp(file: string, f: Frame): void {
  const row = Math.floor((f.w * 3 + 3) / 4) * 4;
  const dataSize = row * f.h;
  const header = Buffer.alloc(54);
  header[0] = 0x42; header[1] = 0x4d;
  header.writeUInt32LE(54 + dataSize, 2);
  header.writeUInt32LE(54, 10);
  header.writeUInt32LE(40, 14);
  header.writeInt32LE(f.w, 18);
  header.writeInt32LE(f.h, 22);
  header.writeUInt16LE(1, 26);
  header.writeUInt16LE(24, 28);
  header.writeUInt32LE(dataSize, 34);
  const body = Buffer.alloc(dataSize);
  for (let y = 0; y < f.h; y++) {
    const dy = f.h - 1 - y;
    for (let x = 0; x < f.w; x++) {
      const src = (y * f.w + x) * 3;
      const dst = dy * row + x * 3;
      body[dst + 0] = clampByte(f.rgb[src + 2]);
      body[dst + 1] = clampByte(f.rgb[src + 1]);
      body[dst + 2] = clampByte(f.rgb[src + 0]);
    }
  }
  fs.writeFileSync(file, Buffer.concat([header, body]));
}
function writeFramePair(base: string, f: Frame, outputs: string[]): void { writeBmp(base + '.bmp', f); writePpm(base + '.ppm', f); outputs.push(path.basename(base + '.bmp'), path.basename(base + '.ppm')); }

function luminance(f: Frame): Float64Array {
  const g = new Float64Array(f.w * f.h);
  for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
    const i = frameIndex(f, x, y, 0);
    g[px(f.w, x, y)] = 0.299 * f.rgb[i] + 0.587 * f.rgb[i + 1] + 0.114 * f.rgb[i + 2];
  }
  return g;
}
function conv(m: Float64Array, w: number, h: number, k: number[]): Float64Array {
  const out = new Float64Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0;
    for (let ky = -1; ky <= 1; ky++) for (let kx = -1; kx <= 1; kx++) {
      const xx = Math.max(0, Math.min(w - 1, x + kx));
      const yy = Math.max(0, Math.min(h - 1, y + ky));
      s += m[px(w, xx, yy)] * k[(ky + 1) * 3 + (kx + 1)];
    }
    out[px(w, x, y)] = s;
  }
  return out;
}
function normalizeMap(m: Float64Array): Float64Array {
  let lo = Infinity, hi = -Infinity;
  for (const v of m) { if (v < lo) lo = v; if (v > hi) hi = v; }
  const span = Math.max(1e-9, hi - lo);
  const out = new Float64Array(m.length);
  for (let i = 0; i < m.length; i++) out[i] = clamp01((m[i] - lo) / span);
  return out;
}
function smoothMap(m: Float64Array, w: number, h: number, passes: number): Float64Array {
  let cur = m;
  const k = [1/16,2/16,1/16,2/16,4/16,2/16,1/16,2/16,1/16];
  for (let i = 0; i < passes; i++) cur = conv(cur, w, h, k);
  return cur;
}
function addWeighted(ms: Float64Array[], ws: number[]): Float64Array { const n = ms[0].length, o = new Float64Array(n); for (let j = 0; j < ms.length; j++) for (let i = 0; i < n; i++) o[i] += ws[j] * ms[j][i]; return o; }
function reluMap(m: Float64Array): Float64Array { const o = new Float64Array(m.length); for (let i = 0; i < m.length; i++) o[i] = Math.max(0, m[i]); return o; }
function shallowActivation(f: Frame): Float64Array {
  const g = luminance(f);
  const sx = conv(g, f.w, f.h, [-1,0,1,-2,0,2,-1,0,1]);
  const sy = conv(g, f.w, f.h, [-1,-2,-1,0,0,0,1,2,1]);
  const lap = conv(g, f.w, f.h, [0,1,0,1,-4,1,0,1,0]);
  const out = new Float64Array(g.length);
  for (let i = 0; i < out.length; i++) out[i] = Math.sqrt(sx[i] * sx[i] + sy[i] * sy[i]) + 0.45 * Math.abs(lap[i]);
  return normalizeMap(smoothMap(out, f.w, f.h, 1));
}
function deepActivation(f: Frame): Float64Array {
  const g = luminance(f);
  const orientedA = reluMap(conv(g, f.w, f.h, [-1,-1,0,-1,0,1,0,1,1]));
  const orientedB = reluMap(conv(g, f.w, f.h, [0,1,1,-1,0,1,-1,-1,0]));
  const edge = shallowActivation(f);
  const layer1 = normalizeMap(addWeighted([orientedA, orientedB, edge], [0.45, 0.45, 0.75]));
  const layer2 = reluMap(conv(layer1, f.w, f.h, [1,-2,1,-2,4,-2,1,-2,1]));
  const pooled = smoothMap(layer2, f.w, f.h, 3);
  return normalizeMap(smoothMap(addWeighted([edge, layer1, normalizeMap(pooled)], [0.35, 0.45, 0.75]), f.w, f.h, 2));
}
function blendMaps(a: Float64Array, b: Float64Array, t: number): Float64Array { const o = new Float64Array(a.length); for (let i = 0; i < o.length; i++) o[i] = (1 - t) * a[i] + t * b[i]; return normalizeMap(o); }
function sampleMap(m: Float64Array, w: number, h: number, x: number, y: number): number { const ix = Math.max(0, Math.min(w - 1, Math.round(x))); const iy = Math.max(0, Math.min(h - 1, Math.round(y))); return m[px(w, ix, iy)]; }
function sampleFrame(f: Frame, x: number, y: number, c: number): number { const ix = Math.max(0, Math.min(f.w - 1, Math.round(x))); const iy = Math.max(0, Math.min(f.h - 1, Math.round(y))); return f.rgb[frameIndex(f, ix, iy, c)]; }
function applyParamTransform(source: Frame, shallow: Float64Array, deep: Float64Array, p: FitParams, seed: number): Frame {
  const control = smoothMap(blendMaps(shallow, deep, p.deepMix), source.w, source.h, Math.max(0, Math.round(2 * p.smoothBlend)));
  const rgb = new Float64Array(source.rgb.length);
  const phaseA = 2 * Math.PI * (((seed * 2654435761) >>> 0) / 4294967296);
  const phaseB = 2 * Math.PI * ((((seed ^ 0x51ed1234) * 2246822519) >>> 0) / 4294967296);
  for (let y = 0; y < source.h; y++) for (let x = 0; x < source.w; x++) {
    const q = px(source.w, x, y);
    const gx = sampleMap(control, source.w, source.h, x + 1, y) - sampleMap(control, source.w, source.h, x - 1, y);
    const gy = sampleMap(control, source.w, source.h, x, y + 1) - sampleMap(control, source.w, source.h, x, y - 1);
    const nx = x / Math.max(1, source.w - 1), ny = y / Math.max(1, source.h - 1);
    const waveX = Math.sin(2 * Math.PI * (8.0 * nx + 3.85 * ny) + phaseA);
    const waveY = Math.cos(2 * Math.PI * (2.4 * nx + 11.0 * ny) + phaseB);
    const amp = p.strength * (0.20 + 0.95 * control[q]);
    const sx = x + amp * (p.gradGain * gx + p.waveGain * waveX);
    const sy = y + amp * (p.gradGain * gy + p.waveGain * waveY);
    const out = q * 3;
    rgb[out + 0] = clamp01(sampleFrame(source, sx, sy, 0) + p.redGain * control[q]);
    rgb[out + 1] = clamp01(sampleFrame(source, sx, sy, 1) + p.greenGain * control[q]);
    rgb[out + 2] = clamp01(sampleFrame(source, sx, sy, 2) + p.blueGain * control[q]);
  }
  return { w: source.w, h: source.h, rgb };
}
function frameLoss(a: Frame, b: Frame): number {
  let s = 0;
  for (let i = 0; i < a.rgb.length; i++) { const d = a.rgb[i] - b.rgb[i]; s += d * d; }
  return s / Math.max(1, a.rgb.length);
}
function edgeLoss(a: Frame, b: Frame): number {
  const la = luminance(a), lb = luminance(b);
  let s = 0, n = 0;
  for (let y = 1; y < a.h; y++) for (let x = 1; x < a.w; x++) {
    const ia = px(a.w, x, y), ja = px(a.w, x - 1, y), ka = px(a.w, x, y - 1);
    const ea = Math.abs(la[ia] - la[ja]) + Math.abs(la[ia] - la[ka]);
    const eb = Math.abs(lb[ia] - lb[ja]) + Math.abs(lb[ia] - lb[ka]);
    const d = ea - eb;
    s += d * d;
    n++;
  }
  return s / Math.max(1, n);
}
function roughness(f: Frame): number {
  const l = luminance(f);
  let s = 0, n = 0;
  for (let y = 1; y < f.h - 1; y++) for (let x = 1; x < f.w - 1; x++) {
    const c = l[px(f.w, x, y)];
    const lap = 4 * c - l[px(f.w, x - 1, y)] - l[px(f.w, x + 1, y)] - l[px(f.w, x, y - 1)] - l[px(f.w, x, y + 1)];
    s += lap * lap;
    n++;
  }
  return s / Math.max(1, n);
}
function complexity(p: FitParams): number { return 0.03 * p.strength * p.strength + 0.01 * p.waveGain * p.waveGain + 0.01 * p.gradGain * p.gradGain + 0.20 * (Math.abs(p.redGain) + Math.abs(p.greenGain) + Math.abs(p.blueGain)); }
function score(source: Frame, target: Frame, candidate: Frame, p: FitParams, req: FitTransformRequest): { total: number; reconstruction: number; regularization: number } {
  const reconstruction = frameLoss(candidate, target);
  const regularization = req.smoothnessWeight * roughness(candidate) + req.edgeWeight * edgeLoss(candidate, target) + req.complexityWeight * complexity(p);
  return { total: reconstruction + regularization, reconstruction, regularization };
}
function mutate(p: FitParams, rng: Rng, temp: number): FitParams {
  const q = cloneParams(p);
  q.strength = bounded(q.strength * Math.exp(0.18 * temp * rng.normal()), 0.05, 3.0);
  q.deepMix = bounded(q.deepMix + 0.14 * temp * rng.normal(), 0, 1);
  q.waveGain = bounded(q.waveGain * Math.exp(0.18 * temp * rng.normal()), 0.05, 7.5);
  q.gradGain = bounded(q.gradGain * Math.exp(0.18 * temp * rng.normal()), 0.5, 32.0);
  q.redGain = bounded(q.redGain + 0.018 * temp * rng.normal(), -0.12, 0.12);
  q.greenGain = bounded(q.greenGain + 0.018 * temp * rng.normal(), -0.12, 0.12);
  q.blueGain = bounded(q.blueGain + 0.018 * temp * rng.normal(), -0.12, 0.12);
  q.smoothBlend = bounded(q.smoothBlend + 0.10 * temp * rng.normal(), 0, 1);
  return q;
}
function initialParams(): FitParams { return { strength: 1.0, deepMix: 0.8, waveGain: 2.3, gradGain: 16.0, redGain: 0.035, greenGain: -0.014, blueGain: -0.020, smoothBlend: 0.2 }; }
function residualFrame(a: Frame, b: Frame): Frame { const rgb = new Float64Array(a.rgb.length); for (let i = 0; i < rgb.length; i++) rgb[i] = clamp01(0.5 + 2.0 * (a.rgb[i] - b.rgb[i])); return { w: a.w, h: a.h, rgb }; }

export function fitTransformToDir(req: FitTransformRequest): FitTransformResult {
  fs.mkdirSync(req.outDir, { recursive: true });
  const source = readFrame(req.sourcePath);
  const target = readFrame(req.targetPath);
  if (source.w !== target.w || source.h !== target.h) throw new Error('fit-transform requires source and target to have the same dimensions');
  const shallow = shallowActivation(source);
  const deep = deepActivation(source);
  const rng = new Rng(req.seed);
  let current = initialParams();
  let currentFrame = applyParamTransform(source, shallow, deep, current, req.seed);
  let currentScore = score(source, target, currentFrame, current, req);
  let best = cloneParams(current);
  let bestFrame = currentFrame;
  let bestScore = currentScore;
  const trace: Array<Record<string, number>> = [];
  for (let i = 0; i < req.trials; i++) {
    const temp = Math.max(0.10, 1.0 - i / Math.max(1, req.trials));
    const cand = mutate(current, rng, temp);
    const candFrame = applyParamTransform(source, shallow, deep, cand, req.seed);
    const candScore = score(source, target, candFrame, cand, req);
    const accept = candScore.total < currentScore.total || rng.next() < Math.exp((currentScore.total - candScore.total) / Math.max(1e-9, 0.0025 * temp));
    if (accept) { current = cand; currentFrame = candFrame; currentScore = candScore; }
    if (candScore.total < bestScore.total) { best = cloneParams(cand); bestFrame = candFrame; bestScore = candScore; }
    trace.push({ trial: i, loss: bestScore.total, reconstruction: bestScore.reconstruction, regularization: bestScore.regularization, strength: best.strength, deepMix: best.deepMix, waveGain: best.waveGain, gradGain: best.gradGain, smoothBlend: best.smoothBlend });
  }
  const outputs: string[] = [];
  writeFramePair(path.join(req.outDir, 'fit_output'), bestFrame, outputs);
  writeFramePair(path.join(req.outDir, 'fit_residual'), residualFrame(bestFrame, target), outputs);
  const result: FitTransformResult = { mode: 'typescript-fit-transform-regularized', source: req.sourcePath, target: req.targetPath, width: source.w, height: source.h, seed: req.seed, trials: req.trials, bestLoss: Number(bestScore.total.toFixed(9)), reconstructionLoss: Number(bestScore.reconstruction.toFixed(9)), regularizationLoss: Number(bestScore.regularization.toFixed(9)), bestParams: best, outputs };
  fs.writeFileSync(path.join(req.outDir, 'fit_report.json'), JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'fit_trace.json'), JSON.stringify(trace, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'fit_support_dictionary.json'), JSON.stringify({ format: 'LS_IMAGE_FIT_SUPPORT_V1', params: best, regularization: { smoothnessWeight: req.smoothnessWeight, edgeWeight: req.edgeWeight, complexityWeight: req.complexityWeight } }, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'fit_summary.txt'), `mode: ${result.mode}\nsource: ${result.source}\ntarget: ${result.target}\nsize: ${result.width}x${result.height}\ntrials: ${result.trials}\nbest_loss: ${result.bestLoss}\nreconstruction_loss: ${result.reconstructionLoss}\nregularization_loss: ${result.regularizationLoss}\n`);
  return result;
}
