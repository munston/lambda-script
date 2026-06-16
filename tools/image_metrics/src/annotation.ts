declare const require: any;
declare const Buffer: any;
const fs = require('fs');
const path = require('path');

interface Frame { w: number; h: number; rgb: Float64Array; }
interface Rect { x0: number; y0: number; x1: number; y1: number; }
interface PatchFeature { patch_id: string; bbox: Rect; area: number; coverage: number; mean_rgb: number[]; mean_luma: number; variance: number; smoothness: number; edge_density: number; texture_variance: number; highlight_ratio: number; chroma: number; x_center: number; y_center: number; centrality: number; labels: string[]; external_label?: string; approved_label?: string; }
interface SegmentResult { mode: string; source: string; width: number; height: number; patch_count: number; outputs: string[]; patches: PatchFeature[]; }
interface LabelRow { image_id: string; patch_id: string; source_tool: string; external_label: string; external_confidence: number; approved_label?: string; features: PatchFeature; }
interface ClassifierModel { format: string; feature_names: string[]; labels: string[]; centroids: Record<string, number[]>; counts: Record<string, number>; created_at: string; }
interface TargetFeature { feature: string; label: string; source_count: number; mean_rgb: number[]; mean_luma: number; smoothness: number; edge_density: number; texture_variance: number; highlight_ratio: number; chroma: number; source_patches: Array<{ image_id: string; patch_id: string; label: string; }>; }

const FEATURE_NAMES = ['mean_r','mean_g','mean_b','mean_luma','variance','smoothness','edge_density','texture_variance','highlight_ratio','chroma','x_center','y_center','centrality'];
const PART_LABELS = ['skin','hair','eye','mouth','breast','arm','hand','leg','foot','garment','background','highlight','boundary','smooth_surface','textured_region'];

function clamp01(x: number): number { return Number.isFinite(x) ? Math.max(0, Math.min(1, x)) : 0; }
function clampByte(x: number): number { return Math.max(0, Math.min(255, Math.round(clamp01(x) * 255))); }
function px(w: number, x: number, y: number): number { return y * w + x; }
function idx(f: Frame, x: number, y: number, c: number): number { return ((y * f.w + x) * 3) + c; }
function ensureDir(p: string): void { fs.mkdirSync(p, { recursive: true }); }
function nowIso(): string { return new Date().toISOString(); }

function syntheticFrame(id: string, w = 192, h = 192): Frame {
  let hash = 2166136261 >>> 0;
  for (let i = 0; i < id.length; i++) { hash ^= id.charCodeAt(i); hash = Math.imul(hash, 16777619) >>> 0; }
  let x = hash | 0;
  function u32(): number { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; return x >>> 0; }
  function next(): number { return u32() / 4294967296; }
  function normal(): number { let u = 0, v = 0; while (u <= 1e-12) u = next(); while (v <= 1e-12) v = next(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
  const rgb = new Float64Array(w * h * 3);
  const phase = (hash % 1000) / 1000;
  for (let y = 0; y < h; y++) for (let xx = 0; xx < w; xx++) {
    const nx = xx / Math.max(1, w - 1), ny = y / Math.max(1, h - 1);
    const base = 0.42 + 0.28 * nx + 0.15 * Math.sin(2 * Math.PI * (nx * 2.3 + ny * 1.7 + phase));
    const centre = Math.exp(-(((nx - 0.52) ** 2) / 0.055 + ((ny - 0.46) ** 2) / 0.080));
    const dark = Math.exp(-(((nx - 0.76) ** 2) / 0.020 + ((ny - 0.55) ** 2) / 0.060));
    const p = (y * w + xx) * 3;
    rgb[p + 0] = clamp01(base + 0.18 * centre - 0.20 * dark + 0.025 * normal());
    rgb[p + 1] = clamp01(base + 0.12 * centre - 0.18 * dark + 0.025 * normal());
    rgb[p + 2] = clamp01(base + 0.08 * centre - 0.14 * dark + 0.025 * normal());
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
  const parsed = readTokens(buf);
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
  const row = Math.floor((w * 3 + 3) / 4) * 4;
  const rgb = new Float64Array(w * h * 3);
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
  throw new Error('annotation commands support synthetic://, .ppm, and 24-bit .bmp inputs');
}
function writePpm(file: string, f: Frame): void {
  const header = Buffer.from(`P6\n${f.w} ${f.h}\n255\n`, 'ascii');
  const body = Buffer.alloc(f.w * f.h * 3);
  for (let i = 0; i < body.length; i++) body[i] = clampByte(f.rgb[i]);
  fs.writeFileSync(file, Buffer.concat([header, body]));
}
function writeBmp(file: string, f: Frame): void {
  const row = Math.floor((f.w * 3 + 3) / 4) * 4, dataSize = row * f.h;
  const header = Buffer.alloc(54);
  header[0] = 0x42; header[1] = 0x4d;
  header.writeUInt32LE(54 + dataSize, 2); header.writeUInt32LE(54, 10); header.writeUInt32LE(40, 14);
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
function cropFrame(f: Frame, r: Rect): Frame {
  const w = Math.max(1, r.x1 - r.x0), h = Math.max(1, r.y1 - r.y0), rgb = new Float64Array(w * h * 3);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) rgb[(y * w + x) * 3 + c] = f.rgb[idx(f, r.x0 + x, r.y0 + y, c)];
  return { w, h, rgb };
}
function maskFrame(w: number, h: number, rect: Rect): Frame {
  const rgb = new Float64Array(w * h * 3);
  for (let y = rect.y0; y < rect.y1; y++) for (let x = rect.x0; x < rect.x1; x++) for (let c = 0; c < 3; c++) rgb[(y * w + x) * 3 + c] = 1;
  return { w, h, rgb };
}
function luminanceAt(f: Frame, x: number, y: number): number {
  const i = idx(f, x, y, 0); return 0.299 * f.rgb[i] + 0.587 * f.rgb[i + 1] + 0.114 * f.rgb[i + 2];
}
function regionFeature(f: Frame, patchId: string, rect: Rect): PatchFeature {
  let sr = 0, sg = 0, sb = 0, sl = 0, sl2 = 0, chroma = 0, hi = 0, edge = 0, nedge = 0;
  const n = Math.max(1, (rect.x1 - rect.x0) * (rect.y1 - rect.y0));
  for (let y = rect.y0; y < rect.y1; y++) for (let x = rect.x0; x < rect.x1; x++) {
    const i = idx(f, x, y, 0), r = f.rgb[i], g = f.rgb[i + 1], b = f.rgb[i + 2], l = 0.299 * r + 0.587 * g + 0.114 * b;
    sr += r; sg += g; sb += b; sl += l; sl2 += l * l; chroma += (Math.abs(r - g) + Math.abs(g - b) + Math.abs(r - b)) / 3; if (l > 0.78) hi++;
    if (x > rect.x0) { edge += Math.abs(l - luminanceAt(f, x - 1, y)); nedge++; }
    if (y > rect.y0) { edge += Math.abs(l - luminanceAt(f, x, y - 1)); nedge++; }
  }
  const mr = sr / n, mg = sg / n, mb = sb / n, ml = sl / n, variance = Math.max(0, sl2 / n - ml * ml), edgeDensity = edge / Math.max(1, nedge);
  const xc = 0.5 * (rect.x0 + rect.x1) / Math.max(1, f.w), yc = 0.5 * (rect.y0 + rect.y1) / Math.max(1, f.h);
  const dx = xc - 0.5, dy = yc - 0.5, centrality = clamp01(1.0 - Math.sqrt(dx * dx + dy * dy) / 0.707);
  const feature: PatchFeature = { patch_id: patchId, bbox: rect, area: n, coverage: n / Math.max(1, f.w * f.h), mean_rgb: [round6(mr), round6(mg), round6(mb)], mean_luma: round6(ml), variance: round6(variance), smoothness: round6(clamp01(1 - variance / 0.08)), edge_density: round6(edgeDensity), texture_variance: round6(clamp01(variance + 1.5 * edgeDensity)), highlight_ratio: round6(hi / n), chroma: round6(chroma / n), x_center: round6(xc), y_center: round6(yc), centrality: round6(centrality), labels: [] };
  feature.labels = deterministicLabels(feature);
  return feature;
}
function round6(x: number): number { return Math.round(x * 1000000) / 1000000; }
function deterministicLabels(f: PatchFeature): string[] {
  const labels: string[] = [];
  const r = f.mean_rgb[0], g = f.mean_rgb[1], b = f.mean_rgb[2];
  const skinLike = r > 0.36 && g > 0.23 && b > 0.16 && r > b * 1.08 && r > g * 0.92 && f.chroma > 0.055 && f.chroma < 0.34;
  const darkHair = f.mean_luma < 0.32 && f.edge_density > 0.025 && f.y_center < 0.55;
  const garment = f.chroma > 0.18 || (f.mean_luma < 0.28 && f.coverage > 0.015);
  const background = f.edge_density < 0.030 && f.centrality < 0.62 && f.coverage > 0.012;
  if (skinLike) labels.push('skin');
  if (darkHair) labels.push('hair');
  if (f.y_center < 0.28 && f.coverage < 0.020 && f.edge_density > 0.055) labels.push('eye');
  if (f.y_center > 0.25 && f.y_center < 0.45 && f.coverage < 0.020 && r > g * 1.05 && f.chroma > 0.12) labels.push('mouth');
  if (skinLike && f.y_center > 0.35 && f.y_center < 0.68 && f.x_center > 0.28 && f.x_center < 0.72) labels.push('breast');
  if (skinLike && f.y_center > 0.35 && f.y_center < 0.85 && (f.x_center < 0.28 || f.x_center > 0.72)) labels.push('arm');
  if (skinLike && f.y_center > 0.62) labels.push('leg');
  if (skinLike && f.coverage < 0.010 && f.y_center > 0.50) labels.push('hand');
  if (skinLike && f.coverage < 0.018 && f.y_center > 0.78) labels.push('foot');
  if (garment) labels.push('garment');
  if (background) labels.push('background');
  if (f.highlight_ratio > 0.16) labels.push('highlight');
  if (f.edge_density > 0.075) labels.push('boundary');
  if (f.smoothness > 0.72) labels.push('smooth_surface');
  if (f.texture_variance > 0.18) labels.push('textured_region');
  if (f.centrality > 0.72) labels.push('central'); else labels.push('peripheral');
  if (!labels.some(x => PART_LABELS.includes(x))) labels.push(f.mean_luma > 0.50 ? 'background' : 'garment');
  return labels;
}
function featureVector(f: PatchFeature): number[] { return [f.mean_rgb[0], f.mean_rgb[1], f.mean_rgb[2], f.mean_luma, f.variance, f.smoothness, f.edge_density, f.texture_variance, f.highlight_ratio, f.chroma, f.x_center, f.y_center, f.centrality]; }
function primaryLabel(f: PatchFeature): string { for (const label of ['skin','eye','mouth','hair','breast','arm','hand','leg','foot','garment','background','highlight','boundary','smooth_surface','textured_region']) if (f.labels.includes(label)) return label; return f.labels[0] || 'unknown'; }
function segmentRects(f: Frame, grid: number): Rect[] {
  const rects: Rect[] = [];
  const step = Math.max(12, Math.floor(Math.min(f.w, f.h) / Math.max(4, grid)));
  for (let y = 0; y < f.h; y += step) for (let x = 0; x < f.w; x += step) rects.push({ x0: x, y0: y, x1: Math.min(f.w, x + step), y1: Math.min(f.h, y + step) });
  return rects;
}
function writeControlMask(file: string, f: Frame, patches: PatchFeature[], scoreByPatch?: Record<string, number>): void {
  const rgb = new Float64Array(f.w * f.h * 3);
  for (const p of patches) {
    const score = scoreByPatch ? clamp01(scoreByPatch[p.patch_id] || 0) : labelScore(p);
    for (let y = p.bbox.y0; y < p.bbox.y1; y++) for (let x = p.bbox.x0; x < p.bbox.x1; x++) {
      const q = (y * f.w + x) * 3; rgb[q + 0] = score; rgb[q + 1] = score; rgb[q + 2] = score;
    }
  }
  writeBmp(file, { w: f.w, h: f.h, rgb });
}
function labelScore(p: PatchFeature): number { return p.labels.includes('skin') ? 0.85 : p.labels.includes('garment') ? 0.55 : p.labels.includes('background') ? 0.18 : 0.35; }

export function segmentImageToDir(imagePath: string, outDir: string, imageId?: string, grid = 10): SegmentResult {
  ensureDir(outDir); ensureDir(path.join(outDir, 'patches')); ensureDir(path.join(outDir, 'segment_masks'));
  const frame = readFrame(imagePath), patches: PatchFeature[] = [], outputs: string[] = [];
  writeBmp(path.join(outDir, 'source.bmp'), frame); writePpm(path.join(outDir, 'source.ppm'), frame); outputs.push('source.bmp', 'source.ppm');
  const rects = segmentRects(frame, grid);
  for (let i = 0; i < rects.length; i++) {
    const pid = `seg_${String(i).padStart(4, '0')}`;
    const feature = regionFeature(frame, pid, rects[i]); patches.push(feature);
    const patchFile = path.join('patches', `${pid}.bmp`); const maskFile = path.join('segment_masks', `${pid}_mask.bmp`);
    writeBmp(path.join(outDir, patchFile), cropFrame(frame, rects[i])); writeBmp(path.join(outDir, maskFile), maskFrame(frame.w, frame.h, rects[i])); outputs.push(patchFile, maskFile);
  }
  writeControlMask(path.join(outDir, 'control_mask.bmp'), frame, patches); outputs.push('control_mask.bmp');
  const result: SegmentResult = { mode: 'typescript-segment-label', source: imagePath, width: frame.w, height: frame.h, patch_count: patches.length, outputs, patches };
  fs.writeFileSync(path.join(outDir, 'segments.json'), JSON.stringify({ image_id: imageId || path.basename(imagePath), width: frame.w, height: frame.h, patches: patches.map(p => ({ patch_id: p.patch_id, bbox: p.bbox, labels: p.labels })) }, null, 2));
  fs.writeFileSync(path.join(outDir, 'patch_features.json'), JSON.stringify({ image_id: imageId || path.basename(imagePath), feature_names: FEATURE_NAMES, patches }, null, 2));
  fs.writeFileSync(path.join(outDir, 'patch_labels.json'), JSON.stringify({ image_id: imageId || path.basename(imagePath), labels: patches.map(p => ({ patch_id: p.patch_id, labels: p.labels, primary_label: primaryLabel(p), confidence: labelScore(p) })) }, null, 2));
  fs.writeFileSync(path.join(outDir, 'segment_summary.txt'), `mode: ${result.mode}\nsource: ${imagePath}\nsize: ${frame.w}x${frame.h}\npatches: ${patches.length}\n`);
  return result;
}

function loadPatchFeatures(runDir: string): { image_id: string; patches: PatchFeature[] } {
  const p = JSON.parse(fs.readFileSync(path.join(runDir, 'patch_features.json'), 'utf-8'));
  return { image_id: String(p.image_id || path.basename(runDir)), patches: p.patches as PatchFeature[] };
}
export function importLabelsToDir(runDir: string, labelsFile: string, sourceTool = 'external_annotation_tool'): { rows: number; output: string } {
  const data = loadPatchFeatures(runDir);
  const raw = JSON.parse(fs.readFileSync(labelsFile, 'utf-8'));
  const items: Array<{ patch_id: string; label?: string; external_label?: string; confidence?: number; external_confidence?: number; approved_label?: string }> = Array.isArray(raw) ? raw : (raw.labels || raw.patches || []);
  const byPatch: Record<string, { label: string; confidence: number; approved_label?: string }> = {};
  for (const item of items) {
    const label = String(item.external_label || item.label || 'unknown');
    byPatch[String(item.patch_id)] = { label, confidence: Number(item.external_confidence || item.confidence || 1), approved_label: item.approved_label };
  }
  const rows: LabelRow[] = [];
  for (const patch of data.patches) {
    const hit = byPatch[patch.patch_id];
    if (!hit) continue;
    patch.external_label = hit.label;
    if (hit.approved_label) patch.approved_label = hit.approved_label;
    rows.push({ image_id: data.image_id, patch_id: patch.patch_id, source_tool: sourceTool, external_label: hit.label, external_confidence: hit.confidence, approved_label: hit.approved_label, features: patch });
  }
  const out = path.join(runDir, 'training_rows.json');
  fs.writeFileSync(out, JSON.stringify({ format: 'LS_PATCH_TRAINING_ROWS_V1', image_id: data.image_id, rows }, null, 2));
  return { rows: rows.length, output: out };
}
function collectTrainingRows(datasetDir: string): LabelRow[] {
  const rows: LabelRow[] = [];
  function walk(dir: string): void {
    for (const name of fs.readdirSync(dir)) {
      const p = path.join(dir, name), st = fs.statSync(p);
      if (st.isDirectory()) walk(p);
      else if (name === 'training_rows.json') {
        const data = JSON.parse(fs.readFileSync(p, 'utf-8'));
        for (const row of data.rows || []) rows.push(row as LabelRow);
      }
    }
  }
  walk(datasetDir);
  return rows;
}
export function trainPatchClassifierToDir(datasetDir: string, outDir: string): ClassifierModel {
  ensureDir(outDir);
  const rows = collectTrainingRows(datasetDir);
  if (!rows.length) throw new Error('no training_rows.json records found');
  const sums: Record<string, number[]> = {}, counts: Record<string, number> = {};
  for (const row of rows) {
    const label = String(row.approved_label || row.external_label || 'unknown');
    const v = featureVector(row.features);
    if (!sums[label]) { sums[label] = FEATURE_NAMES.map(() => 0); counts[label] = 0; }
    for (let i = 0; i < v.length; i++) sums[label][i] += v[i];
    counts[label]++;
  }
  const centroids: Record<string, number[]> = {};
  for (const label of Object.keys(sums)) centroids[label] = sums[label].map(x => round6(x / Math.max(1, counts[label])));
  const model: ClassifierModel = { format: 'LS_PATCH_CLASSIFIER_NEAREST_CENTROID_V1', feature_names: FEATURE_NAMES, labels: Object.keys(centroids).sort(), centroids, counts, created_at: nowIso() };
  fs.writeFileSync(path.join(outDir, 'patch_classifier.json'), JSON.stringify(model, null, 2));
  fs.writeFileSync(path.join(outDir, 'classifier_summary.txt'), `format: ${model.format}\nlabels: ${model.labels.join(', ')}\nrows: ${rows.length}\n`);
  return model;
}
function loadClassifier(modelPath: string): ClassifierModel { return JSON.parse(fs.readFileSync(modelPath, 'utf-8')) as ClassifierModel; }
function classifyPatch(model: ClassifierModel, f: PatchFeature): { label: string; confidence: number; scores: Record<string, number> } {
  const v = featureVector(f), scores: Record<string, number> = {};
  let best = 'unknown', bestScore = -Infinity, second = -Infinity;
  for (const label of model.labels) {
    const c = model.centroids[label];
    let d = 0;
    for (let i = 0; i < v.length; i++) { const z = v[i] - c[i]; d += z * z; }
    const s = Math.exp(-3.0 * Math.sqrt(d));
    scores[label] = round6(s);
    if (s > bestScore) { second = bestScore; bestScore = s; best = label; } else if (s > second) second = s;
  }
  return { label: best, confidence: round6(clamp01(bestScore - Math.max(0, second) + 0.50 * bestScore)), scores };
}
export function segmentPredictToDir(imagePath: string, modelPath: string, outDir: string, grid = 10): { patch_count: number; output: string } {
  const seg = segmentImageToDir(imagePath, outDir, path.basename(imagePath), grid);
  const model = loadClassifier(modelPath);
  const patchScores: Array<{ patch_id: string; predicted_label: string; confidence: number; scores: Record<string, number> }> = [];
  const controlScores: Record<string, number> = {};
  for (const patch of seg.patches) {
    const c = classifyPatch(model, patch);
    patchScores.push({ patch_id: patch.patch_id, predicted_label: c.label, confidence: c.confidence, scores: c.scores });
    controlScores[patch.patch_id] = c.confidence;
  }
  const frame = readFrame(imagePath);
  writeControlMask(path.join(outDir, 'part_score_control_mask.bmp'), frame, seg.patches, controlScores);
  const out = path.join(outDir, 'patch_scores.json');
  fs.writeFileSync(out, JSON.stringify({ model: modelPath, patches: patchScores }, null, 2));
  fs.writeFileSync(path.join(outDir, 'predict_summary.txt'), `mode: segment-predict\nsource: ${imagePath}\nmodel: ${modelPath}\npatches: ${patchScores.length}\n`);
  return { patch_count: patchScores.length, output: out };
}
export function buildTargetsToDir(datasetDir: string, outDir: string, feature: string, label: string): { feature: string; target_count: number; output: string } {
  ensureDir(outDir);
  const rows = collectTrainingRows(datasetDir);
  const selected = rows.filter(r => String(r.approved_label || r.external_label) === label || r.features.labels.includes(label));
  if (!selected.length) throw new Error(`no patches found for label ${label}`);
  function avg(fn: (f: PatchFeature) => number): number { return round6(selected.reduce((a, r) => a + fn(r.features), 0) / selected.length); }
  const target: TargetFeature = { feature, label, source_count: selected.length, mean_rgb: [avg(f => f.mean_rgb[0]), avg(f => f.mean_rgb[1]), avg(f => f.mean_rgb[2])], mean_luma: avg(f => f.mean_luma), smoothness: avg(f => f.smoothness), edge_density: avg(f => f.edge_density), texture_variance: avg(f => f.texture_variance), highlight_ratio: avg(f => f.highlight_ratio), chroma: avg(f => f.chroma), source_patches: selected.map(r => ({ image_id: r.image_id, patch_id: r.patch_id, label: String(r.approved_label || r.external_label) })) };
  const out = path.join(outDir, 'target_features.json');
  fs.writeFileSync(out, JSON.stringify({ format: 'LS_TARGET_FEATURES_V1', targets: [target] }, null, 2));
  fs.writeFileSync(path.join(outDir, 'target_summary.txt'), `feature: ${feature}\nlabel: ${label}\nsource_count: ${selected.length}\nmean_rgb: ${target.mean_rgb.join(',')}\n`);
  return { feature, target_count: selected.length, output: out };
}
function findTarget(targetsPath: string, feature: string): TargetFeature {
  const data = JSON.parse(fs.readFileSync(targetsPath, 'utf-8'));
  const targets = data.targets || [];
  const target = targets.find((t: TargetFeature) => t.feature === feature) || targets[0];
  if (!target) throw new Error('target feature dictionary is empty');
  return target as TargetFeature;
}
export function matchFeatureToDir(imagePath: string, targetsPath: string, feature: string, outDir: string, label = 'skin', strength = 0.75): { output: string; matched_patches: number } {
  ensureDir(outDir);
  const frame = readFrame(imagePath);
  const target = findTarget(targetsPath, feature);
  const seg = segmentImageToDir(imagePath, path.join(outDir, 'segmentation'), path.basename(imagePath), 10);
  const outFrame: Frame = { w: frame.w, h: frame.h, rgb: new Float64Array(frame.rgb) };
  let matched = 0;
  for (const patch of seg.patches) {
    if (!(patch.labels.includes(label) || patch.labels.includes(target.label))) continue;
    matched++;
    const delta = [target.mean_rgb[0] - patch.mean_rgb[0], target.mean_rgb[1] - patch.mean_rgb[1], target.mean_rgb[2] - patch.mean_rgb[2]];
    for (let y = patch.bbox.y0; y < patch.bbox.y1; y++) for (let x = patch.bbox.x0; x < patch.bbox.x1; x++) for (let c = 0; c < 3; c++) {
      const i = idx(outFrame, x, y, c);
      outFrame.rgb[i] = clamp01(outFrame.rgb[i] + strength * delta[c]);
    }
  }
  writeBmp(path.join(outDir, 'match_feature_output.bmp'), outFrame);
  writePpm(path.join(outDir, 'match_feature_output.ppm'), outFrame);
  const report = { mode: 'match-feature', source: imagePath, targets: targetsPath, feature, label, target, matched_patches: matched, output: 'match_feature_output.bmp' };
  fs.writeFileSync(path.join(outDir, 'match_feature_report.json'), JSON.stringify(report, null, 2));
  fs.writeFileSync(path.join(outDir, 'match_feature_summary.txt'), `feature: ${feature}\nlabel: ${label}\nmatched_patches: ${matched}\n`);
  return { output: path.join(outDir, 'match_feature_output.bmp'), matched_patches: matched };
}
