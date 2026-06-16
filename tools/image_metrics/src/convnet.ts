declare const require: any;
declare const Buffer: any;
const fs = require('fs');
const path = require('path');

export interface Frame { w: number; h: number; rgb: Float64Array; }
export interface ConvnetRequest { imagePath: string; outDir: string; seed: number; shallowStrength: number; deepStrength: number; }
export interface ConvnetResult { mode: string; source: string; width: number; height: number; seed: number; outputs: string[]; shallow: Record<string, number>; deep: Record<string, number>; }

class Rng {
  private x: number;
  constructor(seed: number) { this.x = seed | 0 || 123456789; }
  u32(): number { let x = this.x | 0; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; this.x = x | 0; return this.x >>> 0; }
  next(): number { return this.u32() / 4294967296; }
  normal(): number { let u = 0, v = 0; while (u <= 1e-12) u = this.next(); while (v <= 1e-12) v = this.next(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
}

function clamp01(x: number): number { return Number.isFinite(x) ? Math.max(0, Math.min(1, x)) : 0; }
function clampByte(x: number): number { return Math.max(0, Math.min(255, Math.round(clamp01(x) * 255))); }
function idx(f: Frame, x: number, y: number, c: number): number { return ((y * f.w + x) * 3) + c; }
function px(w: number, x: number, y: number): number { return y * w + x; }
function sampleMap(m: Float64Array, w: number, h: number, x: number, y: number): number {
  const ix = Math.max(0, Math.min(w - 1, Math.round(x)));
  const iy = Math.max(0, Math.min(h - 1, Math.round(y)));
  return m[px(w, ix, iy)];
}
function sampleFrame(f: Frame, x: number, y: number, c: number): number {
  const ix = Math.max(0, Math.min(f.w - 1, Math.round(x)));
  const iy = Math.max(0, Math.min(f.h - 1, Math.round(y)));
  return f.rgb[idx(f, ix, iy, c)];
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
  const { tokens, offset } = readTokens(buf);
  if (tokens[0] !== 'P6') throw new Error('PPM reader only supports P6');
  const w = Number(tokens[1]), h = Number(tokens[2]), maxv = Number(tokens[3]);
  if (!w || !h || !maxv) throw new Error('invalid PPM header');
  const rgb = new Float64Array(w * h * 3);
  for (let i = 0; i < rgb.length; i++) rgb[i] = Number(buf[offset + i] || 0) / maxv;
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

function readFrame(imagePath: string): Frame {
  if (imagePath.startsWith('synthetic://')) return syntheticFrame(imagePath);
  const ext = path.extname(imagePath).toLowerCase();
  if (ext === '.ppm') return readPpm(imagePath);
  if (ext === '.bmp') return readBmp(imagePath);
  throw new Error('TypeScript convnet-distortion supports synthetic://, .ppm, and 24-bit .bmp inputs; convert JPEG/PNG through image-metrics analyze/stochastic-update first');
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

function writeFramePair(base: string, f: Frame, outputs: string[]): void {
  writeBmp(base + '.bmp', f); outputs.push(path.basename(base + '.bmp'));
  writePpm(base + '.ppm', f); outputs.push(path.basename(base + '.ppm'));
}

function luminance(f: Frame): Float64Array {
  const g = new Float64Array(f.w * f.h);
  for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
    const i = idx(f, x, y, 0);
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

function activationStats(m: Float64Array): Record<string, number> {
  let sum = 0, max = 0, active = 0;
  for (const v of m) { sum += v; if (v > max) max = v; if (v > 0.55) active++; }
  return { mean: Number((sum / Math.max(1, m.length)).toFixed(6)), max: Number(max.toFixed(6)), active_fraction: Number((active / Math.max(1, m.length)).toFixed(6)) };
}

function shallowActivation(f: Frame): Float64Array {
  const g = luminance(f);
  const sx = conv(g, f.w, f.h, [-1,0,1,-2,0,2,-1,0,1]);
  const sy = conv(g, f.w, f.h, [-1,-2,-1,0,0,0,1,2,1]);
  const lap = conv(g, f.w, f.h, [0,1,0,1,-4,1,0,1,0]);
  const out = new Float64Array(g.length);
  for (let i = 0; i < out.length; i++) out[i] = Math.sqrt(sx[i] * sx[i] + sy[i] * sy[i]) + 0.45 * Math.abs(lap[i]);
  return normalizeMap(smoothMap(out, f.w, f.h, 1));
}

function reluMap(m: Float64Array): Float64Array { const o = new Float64Array(m.length); for (let i = 0; i < m.length; i++) o[i] = Math.max(0, m[i]); return o; }
function addWeighted(ms: Float64Array[], ws: number[]): Float64Array { const n = ms[0].length, o = new Float64Array(n); for (let j = 0; j < ms.length; j++) for (let i = 0; i < n; i++) o[i] += ws[j] * ms[j][i]; return o; }

function deepActivation(f: Frame): Float64Array {
  const g = luminance(f);
  const orientedA = reluMap(conv(g, f.w, f.h, [-1,-1,0,-1,0,1,0,1,1]));
  const orientedB = reluMap(conv(g, f.w, f.h, [0,1,1,-1,0,1,-1,-1,0]));
  const edge = shallowActivation(f);
  const layer1 = normalizeMap(addWeighted([orientedA, orientedB, edge], [0.45, 0.45, 0.75]));
  const layer2 = reluMap(conv(layer1, f.w, f.h, [1,-2,1,-2,4,-2,1,-2,1]));
  const pooled = smoothMap(layer2, f.w, f.h, 3);
  const recurrent = addWeighted([edge, layer1, normalizeMap(pooled)], [0.35, 0.45, 0.75]);
  return normalizeMap(smoothMap(recurrent, f.w, f.h, 2));
}

function maskFrame(m: Float64Array, w: number, h: number): Frame {
  const rgb = new Float64Array(w * h * 3);
  for (let i = 0; i < m.length; i++) { rgb[i * 3 + 0] = m[i]; rgb[i * 3 + 1] = m[i]; rgb[i * 3 + 2] = m[i]; }
  return { w, h, rgb };
}

function overlay(f: Frame, m: Float64Array, alpha: number, high: boolean): Frame {
  const rgb = new Float64Array(f.rgb.length);
  for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
    const p = px(f.w, x, y);
    const q = p * 3;
    const a = clamp01(m[p] * alpha);
    const hr = high ? 1.0 : 0.85, hg = high ? 0.15 : 0.35, hb = high ? 0.05 : 0.95;
    rgb[q + 0] = clamp01(f.rgb[q + 0] * (1 - a) + hr * a);
    rgb[q + 1] = clamp01(f.rgb[q + 1] * (1 - a) + hg * a);
    rgb[q + 2] = clamp01(f.rgb[q + 2] * (1 - a) + hb * a);
  }
  return { w: f.w, h: f.h, rgb };
}

function distort(f: Frame, m: Float64Array, strength: number, seed: number, deep: boolean): Frame {
  const rng = new Rng(seed ^ (deep ? 0x51ed1234 : 0x2a11c0de));
  const rgb = new Float64Array(f.rgb.length);
  const phaseA = 2 * Math.PI * rng.next(), phaseB = 2 * Math.PI * rng.next();
  const freqA = deep ? 8.0 : 4.0, freqB = deep ? 11.0 : 5.5;
  for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
    const p = px(f.w, x, y);
    const gx = sampleMap(m, f.w, f.h, x + 1, y) - sampleMap(m, f.w, f.h, x - 1, y);
    const gy = sampleMap(m, f.w, f.h, x, y + 1) - sampleMap(m, f.w, f.h, x, y - 1);
    const nx = x / Math.max(1, f.w - 1), ny = y / Math.max(1, f.h - 1);
    const waveX = Math.sin(2 * Math.PI * (freqA * nx + 0.35 * freqB * ny) + phaseA);
    const waveY = Math.cos(2 * Math.PI * (0.30 * freqA * nx + freqB * ny) + phaseB);
    const amp = strength * (0.20 + 0.95 * m[p]);
    const sx = x + amp * (18.0 * gx + (deep ? 2.8 : 1.4) * waveX);
    const sy = y + amp * (18.0 * gy + (deep ? 2.8 : 1.4) * waveY);
    const q = p * 3;
    for (let c = 0; c < 3; c++) {
      const base = sampleFrame(f, sx, sy, c);
      const chromaPush = deep ? (c === 0 ? 0.045 : c === 1 ? -0.018 : -0.026) : (c === 2 ? 0.018 : 0.0);
      rgb[q + c] = clamp01(base + chromaPush * m[p]);
    }
  }
  return { w: f.w, h: f.h, rgb };
}

function gridOverlay(f: Frame, m: Float64Array, spacing: number): Frame {
  const out = overlay(f, m, 1.15, true);
  for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
    const grid = x % spacing === 0 || y % spacing === 0;
    if (!grid) continue;
    const q = (y * f.w + x) * 3;
    out.rgb[q + 0] = clamp01(0.05 + 0.90 * out.rgb[q + 0]);
    out.rgb[q + 1] = clamp01(0.95);
    out.rgb[q + 2] = clamp01(0.95);
  }
  return out;
}

export function convnetDistortionToDir(req: ConvnetRequest): ConvnetResult {
  fs.mkdirSync(req.outDir, { recursive: true });
  const src = readFrame(req.imagePath);
  const outputs: string[] = [];
  const shallow = shallowActivation(src);
  const deep = deepActivation(src);
  const shallowDistorted = distort(src, shallow, req.shallowStrength, req.seed, false);
  const deepDistorted = distort(src, deep, req.deepStrength, req.seed, true);
  writeFramePair(path.join(req.outDir, 'source'), src, outputs);
  writeFramePair(path.join(req.outDir, 'shallow_convnet_distortion'), shallowDistorted, outputs);
  writeFramePair(path.join(req.outDir, 'shallow_convnet_activation_mask'), maskFrame(shallow, src.w, src.h), outputs);
  writeFramePair(path.join(req.outDir, 'shallow_convnet_activation_overlay'), overlay(src, shallow, 0.80, false), outputs);
  writeFramePair(path.join(req.outDir, 'deeper_convnet_distortion'), deepDistorted, outputs);
  writeFramePair(path.join(req.outDir, 'deeper_convnet_activation_mask'), maskFrame(deep, src.w, src.h), outputs);
  writeFramePair(path.join(req.outDir, 'deeper_convnet_high_overlay'), overlay(src, deep, 1.20, true), outputs);
  writeFramePair(path.join(req.outDir, 'deeper_convnet_high_overlay_grid'), gridOverlay(deepDistorted, deep, 16), outputs);
  const result: ConvnetResult = {
    mode: 'typescript-convnet-distortion',
    source: req.imagePath,
    width: src.w,
    height: src.h,
    seed: req.seed,
    outputs,
    shallow: activationStats(shallow),
    deep: activationStats(deep),
  };
  fs.writeFileSync(path.join(req.outDir, 'convnet_report.json'), JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'convnet_summary.txt'), `mode: ${result.mode}\nsource: ${result.source}\nsize: ${result.width}x${result.height}\nseed: ${result.seed}\nshallow_mean: ${result.shallow.mean}\ndeep_mean: ${result.deep.mean}\noutputs: ${result.outputs.length}\n`);
  return result;
}
