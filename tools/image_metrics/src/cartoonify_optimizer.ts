declare const require: any;
declare const Buffer: any;
const fs = require('fs');
const path = require('path');

interface Frame { w: number; h: number; rgb: Float64Array; }
interface Rect { x0: number; y0: number; x1: number; y1: number; }
interface LayerParams { smooth: number; posterize: number; edgeInk: number; saturation: number; brightness: number; control: number; }
interface LayerRecord { layer: number; patch_id: string; before: number; after: number; accepted: boolean; params: LayerParams; }
export interface CartoonifyRequest { imagePath: string; outDir: string; seed: number; layers: number; grid: number; tries: number; metric: string; }
export interface CartoonifyResult { mode: string; source: string; width: number; height: number; seed: number; layers: number; grid: number; tries: number; metric: string; globalScore: number; outputs: string[]; }

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
function idx(f: Frame, x: number, y: number, c: number): number { return ((y * f.w + x) * 3) + c; }
function ensureDir(p: string): void { fs.mkdirSync(p, { recursive: true }); }
function round6(x: number): number { return Math.round(x * 1000000) / 1000000; }
function bounded(x: number, lo: number, hi: number): number { return Math.max(lo, Math.min(hi, x)); }
function cloneParams(p: LayerParams): LayerParams { return { smooth: p.smooth, posterize: p.posterize, edgeInk: p.edgeInk, saturation: p.saturation, brightness: p.brightness, control: p.control }; }

function syntheticFrame(id: string, w = 192, h = 192): Frame {
  let hash = 2166136261 >>> 0;
  for (let i = 0; i < id.length; i++) { hash ^= id.charCodeAt(i); hash = Math.imul(hash, 16777619) >>> 0; }
  const rng = new Rng(hash | 0), rgb = new Float64Array(w * h * 3), phase = (hash % 1000) / 1000;
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
  const buf = fs.readFileSync(file), parsed = readTokens(buf);
  if (parsed.tokens[0] !== 'P6') throw new Error('PPM reader only supports P6');
  const w = Number(parsed.tokens[1]), h = Number(parsed.tokens[2]), maxv = Number(parsed.tokens[3]);
  if (!w || !h || !maxv) throw new Error('invalid PPM header');
  const rgb = new Float64Array(w * h * 3);
  for (let i = 0; i < rgb.length; i++) rgb[i] = Number(buf[parsed.offset + i] || 0) / maxv;
  return { w, h, rgb };
}
function readBmp(file: string): Frame {
  const buf = fs.readFileSync(file);
  if (buf[0] !== 0x42 || buf[1] !== 0x4d) throw new Error('invalid BMP header');
  const off = buf.readUInt32LE(10), w = buf.readInt32LE(18), rawH = buf.readInt32LE(22), h = Math.abs(rawH), bpp = buf.readUInt16LE(28);
  if (bpp !== 24) throw new Error('BMP reader only supports 24-bit BMP');
  const row = Math.floor((w * 3 + 3) / 4) * 4, rgb = new Float64Array(w * h * 3);
  for (let y = 0; y < h; y++) {
    const sy = rawH > 0 ? h - 1 - y : y;
    for (let x = 0; x < w; x++) {
      const src = off + sy * row + x * 3, dst = (y * w + x) * 3;
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
  throw new Error('cartoonify-optimize supports synthetic://, .ppm, and 24-bit .bmp inputs');
}
function writePpm(file: string, f: Frame): void {
  const header = Buffer.from(`P6\n${f.w} ${f.h}\n255\n`, 'ascii'), body = Buffer.alloc(f.w * f.h * 3);
  for (let i = 0; i < body.length; i++) body[i] = clampByte(f.rgb[i]);
  fs.writeFileSync(file, Buffer.concat([header, body]));
}
function writeBmp(file: string, f: Frame): void {
  const row = Math.floor((f.w * 3 + 3) / 4) * 4, dataSize = row * f.h, header = Buffer.alloc(54);
  header[0] = 0x42; header[1] = 0x4d; header.writeUInt32LE(54 + dataSize, 2); header.writeUInt32LE(54, 10); header.writeUInt32LE(40, 14);
  header.writeInt32LE(f.w, 18); header.writeInt32LE(f.h, 22); header.writeUInt16LE(1, 26); header.writeUInt16LE(24, 28); header.writeUInt32LE(dataSize, 34);
  const body = Buffer.alloc(dataSize);
  for (let y = 0; y < f.h; y++) {
    const dy = f.h - 1 - y;
    for (let x = 0; x < f.w; x++) {
      const src = (y * f.w + x) * 3, dst = dy * row + x * 3;
      body[dst + 0] = clampByte(f.rgb[src + 2]); body[dst + 1] = clampByte(f.rgb[src + 1]); body[dst + 2] = clampByte(f.rgb[src + 0]);
    }
  }
  fs.writeFileSync(file, Buffer.concat([header, body]));
}
function writeFramePair(base: string, f: Frame, outputs: string[]): void { writeBmp(base + '.bmp', f); writePpm(base + '.ppm', f); outputs.push(path.basename(base + '.bmp'), path.basename(base + '.ppm')); }
function luminanceAt(f: Frame, x: number, y: number): number { const i = idx(f, x, y, 0); return 0.299 * f.rgb[i] + 0.587 * f.rgb[i + 1] + 0.114 * f.rgb[i + 2]; }
function rectsFor(f: Frame, grid: number): Rect[] {
  const out: Rect[] = [], step = Math.max(12, Math.floor(Math.min(f.w, f.h) / Math.max(2, grid)));
  for (let y = 0; y < f.h; y += step) for (let x = 0; x < f.w; x += step) out.push({ x0: x, y0: y, x1: Math.min(f.w, x + step), y1: Math.min(f.h, y + step) });
  return out;
}
function subFrame(f: Frame, r: Rect): Frame {
  const w = Math.max(1, r.x1 - r.x0), h = Math.max(1, r.y1 - r.y0), rgb = new Float64Array(w * h * 3);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) rgb[(y * w + x) * 3 + c] = f.rgb[idx(f, r.x0 + x, r.y0 + y, c)];
  return { w, h, rgb };
}
function paste(f: Frame, r: Rect, patch: Frame, alpha: number): void {
  for (let y = 0; y < patch.h; y++) for (let x = 0; x < patch.w; x++) for (let c = 0; c < 3; c++) {
    const dst = idx(f, r.x0 + x, r.y0 + y, c), src = (y * patch.w + x) * 3 + c;
    f.rgb[dst] = clamp01((1 - alpha) * f.rgb[dst] + alpha * patch.rgb[src]);
  }
}
function blurPatch(p: Frame, amount: number): Frame {
  const out = { w: p.w, h: p.h, rgb: new Float64Array(p.rgb) };
  const passes = Math.max(0, Math.round(amount));
  for (let pass = 0; pass < passes; pass++) {
    const src = new Float64Array(out.rgb);
    for (let y = 0; y < p.h; y++) for (let x = 0; x < p.w; x++) for (let c = 0; c < 3; c++) {
      let s = 0, n = 0;
      for (let yy = -1; yy <= 1; yy++) for (let xx = -1; xx <= 1; xx++) {
        const qx = Math.max(0, Math.min(p.w - 1, x + xx)), qy = Math.max(0, Math.min(p.h - 1, y + yy));
        const w = xx === 0 && yy === 0 ? 4 : (xx === 0 || yy === 0 ? 2 : 1);
        s += w * src[(qy * p.w + qx) * 3 + c]; n += w;
      }
      out.rgb[(y * p.w + x) * 3 + c] = s / n;
    }
  }
  return out;
}
function edgeMap(p: Frame): Float64Array {
  const e = new Float64Array(p.w * p.h);
  for (let y = 0; y < p.h; y++) for (let x = 0; x < p.w; x++) {
    const l = luminanceAt(p, x, y), lx = luminanceAt(p, Math.max(0, x - 1), y), ly = luminanceAt(p, x, Math.max(0, y - 1));
    e[px(p.w, x, y)] = Math.min(1, 4.0 * (Math.abs(l - lx) + Math.abs(l - ly)));
  }
  return e;
}
function transformPatch(p: Frame, params: LayerParams): Frame {
  const blurred = blurPatch(p, params.smooth);
  const edges = edgeMap(p);
  const out = { w: p.w, h: p.h, rgb: new Float64Array(p.rgb.length) };
  const levels = Math.max(2, Math.round(3 + 6 * (1 - params.posterize)));
  for (let y = 0; y < p.h; y++) for (let x = 0; x < p.w; x++) {
    const q = (y * p.w + x) * 3, edge = edges[px(p.w, x, y)];
    const r = blurred.rgb[q], g = blurred.rgb[q + 1], b = blurred.rgb[q + 2], lum = 0.299 * r + 0.587 * g + 0.114 * b;
    let rr = Math.round(r * (levels - 1)) / (levels - 1), gg = Math.round(g * (levels - 1)) / (levels - 1), bb = Math.round(b * (levels - 1)) / (levels - 1);
    rr = lum + (rr - lum) * params.saturation; gg = lum + (gg - lum) * params.saturation; bb = lum + (bb - lum) * params.saturation;
    const ink = clamp01(edge * params.edgeInk);
    out.rgb[q + 0] = clamp01((rr + params.brightness) * (1 - ink));
    out.rgb[q + 1] = clamp01((gg + params.brightness) * (1 - ink));
    out.rgb[q + 2] = clamp01((bb + params.brightness) * (1 - ink));
  }
  return out;
}
function patchStats(p: Frame): { variance: number; edge: number; palette: number; saturation: number; } {
  let sl = 0, sl2 = 0, edge = 0, sat = 0, nedge = 0;
  const seen: Record<string, number> = {};
  for (let y = 0; y < p.h; y++) for (let x = 0; x < p.w; x++) {
    const i = idx(p, x, y, 0), r = p.rgb[i], g = p.rgb[i + 1], b = p.rgb[i + 2], lum = 0.299 * r + 0.587 * g + 0.114 * b;
    sl += lum; sl2 += lum * lum; sat += Math.max(r, g, b) - Math.min(r, g, b);
    const key = `${Math.round(r * 5)}:${Math.round(g * 5)}:${Math.round(b * 5)}`; seen[key] = 1;
    if (x > 0) { edge += Math.abs(lum - luminanceAt(p, x - 1, y)); nedge++; }
    if (y > 0) { edge += Math.abs(lum - luminanceAt(p, x, y - 1)); nedge++; }
  }
  const n = Math.max(1, p.w * p.h), mean = sl / n, variance = Math.max(0, sl2 / n - mean * mean);
  return { variance, edge: edge / Math.max(1, nedge), palette: Object.keys(seen).length / n, saturation: sat / n };
}
function cartoonMetric(p: Frame): number {
  const s = patchStats(p);
  const flat = clamp01(1 - s.variance / 0.055), clearEdge = clamp01(s.edge / 0.090), palette = clamp01(1 - s.palette / 0.20), sat = clamp01(s.saturation / 0.22);
  return round6(0.35 * flat + 0.28 * clearEdge + 0.25 * palette + 0.12 * sat);
}
function mutate(p: LayerParams, rng: Rng, scale: number): LayerParams {
  const q = cloneParams(p);
  q.smooth = bounded(q.smooth + 0.95 * scale * rng.normal(), 0, 4.5);
  q.posterize = bounded(q.posterize + 0.20 * scale * rng.normal(), 0, 1);
  q.edgeInk = bounded(q.edgeInk + 0.35 * scale * rng.normal(), 0, 2.8);
  q.saturation = bounded(q.saturation + 0.22 * scale * rng.normal(), 0.45, 1.75);
  q.brightness = bounded(q.brightness + 0.035 * scale * rng.normal(), -0.10, 0.10);
  q.control = bounded(q.control + 0.20 * scale * rng.normal(), 0.15, 1.0);
  return q;
}
function initialParams(layer: number): LayerParams { return { smooth: 0.7 + 0.45 * layer, posterize: 0.65, edgeInk: 0.6 + 0.15 * layer, saturation: 1.08, brightness: 0.0, control: 0.85 }; }
function globalMetric(f: Frame, rects: Rect[]): number { let s = 0; for (const r of rects) s += cartoonMetric(subFrame(f, r)); return round6(s / Math.max(1, rects.length)); }

export function cartoonifyOptimizeToDir(req: CartoonifyRequest): CartoonifyResult {
  ensureDir(req.outDir);
  const original = readFrame(req.imagePath);
  const current: Frame = { w: original.w, h: original.h, rgb: new Float64Array(original.rgb) };
  const rects = rectsFor(original, req.grid);
  const rng = new Rng(req.seed), records: LayerRecord[] = [];
  for (let layer = 0; layer < req.layers; layer++) {
    for (let pi = 0; pi < rects.length; pi++) {
      const rect = rects[pi], beforePatch = subFrame(current, rect), beforeScore = cartoonMetric(beforePatch);
      let bestParams = initialParams(layer), bestPatch = transformPatch(beforePatch, bestParams), bestScore = cartoonMetric(bestPatch);
      for (let t = 0; t < req.tries; t++) {
        const candParams = mutate(bestParams, rng, Math.max(0.18, 1 - t / Math.max(1, req.tries)));
        const candPatch = transformPatch(beforePatch, candParams), candScore = cartoonMetric(candPatch);
        if (candScore > bestScore) { bestParams = candParams; bestPatch = candPatch; bestScore = candScore; }
      }
      const accepted = bestScore > beforeScore;
      if (accepted) paste(current, rect, bestPatch, bestParams.control);
      records.push({ layer, patch_id: `seg_${String(pi).padStart(4, '0')}`, before: beforeScore, after: accepted ? bestScore : beforeScore, accepted, params: bestParams });
    }
  }
  const outputs: string[] = [];
  writeFramePair(path.join(req.outDir, 'cartoonify_output'), current, outputs);
  writeFramePair(path.join(req.outDir, 'cartoonify_source'), original, outputs);
  const score = globalMetric(current, rects);
  const result: CartoonifyResult = { mode: 'typescript-layered-stochastic-cartoonify', source: req.imagePath, width: original.w, height: original.h, seed: req.seed, layers: req.layers, grid: req.grid, tries: req.tries, metric: req.metric, globalScore: score, outputs };
  fs.writeFileSync(path.join(req.outDir, 'cartoonify_report.json'), JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'cartoonify_layer_trace.json'), JSON.stringify(records, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'cartoonify_summary.txt'), `mode: ${result.mode}\nsource: ${result.source}\nsize: ${result.width}x${result.height}\nlayers: ${result.layers}\ngrid: ${result.grid}\ntries: ${result.tries}\nglobal_score: ${result.globalScore}\n`);
  return result;
}
