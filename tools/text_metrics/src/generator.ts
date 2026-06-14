import { seedCorpus, corpusText, corpusSummary } from './corpus';
import { computeTextMetric } from './metrics';

export interface GeneratorOptions {
  seedText?: string;
  maxTokens?: number;
  temperature?: number;
  seed?: number;
  minScore?: number;
}

export interface GeneratedPrompt {
  text: string;
  score: number;
  attempts: number;
  tokens: number;
  matrix: MatrixStats;
  repaired: boolean;
}

export interface MatrixStats {
  vocabulary: number;
  edges: number;
  maxContext: number;
  storage: 'sparse-token-transition-map';
}

type Row = Map<number, number>;

interface TinyModel {
  tokenToId: Map<string, number>;
  idToToken: string[];
  rows: Map<number, Row>;
  starts: number[];
  stats: MatrixStats;
}

function normaliseForTokens(text: string): string {
  return text.replace(/[“”]/g, '"').replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim();
}

export function tokenizeForGeneration(text: string): string[] {
  const s = normaliseForTokens(text);
  return s.match(/[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?|[.,;:()]/g) ?? [];
}

function detokenize(tokens: string[]): string {
  let out = '';
  for (const tok of tokens) {
    if (!out) out = tok;
    else if (/^[.,;:)]$/.test(tok)) out += tok;
    else if (tok === '(') out += ' ' + tok;
    else out += ' ' + tok;
  }
  return out.replace(/\s+([.,;:])/g, '$1').trim();
}

function addToken(model: TinyModel, tok: string): number {
  const key = tok.toLowerCase();
  const existing = model.tokenToId.get(key);
  if (existing !== undefined) return existing;
  const id = model.idToToken.length;
  model.tokenToId.set(key, id);
  model.idToToken.push(tok);
  return id;
}

function addEdge(model: TinyModel, a: number, b: number, weight: number): void {
  const row = model.rows.get(a) ?? new Map<number, number>();
  row.set(b, (row.get(b) ?? 0) + weight);
  model.rows.set(a, row);
}

export function buildTinyCausalModel(extraTexts: string[] = []): TinyModel {
  const model: TinyModel = {
    tokenToId: new Map(),
    idToToken: [],
    rows: new Map(),
    starts: [],
    stats: { vocabulary: 0, edges: 0, maxContext: 1, storage: 'sparse-token-transition-map' }
  };
  const texts = [...corpusText(['prompt', 'repair']), ...extraTexts.filter(s => s.trim().length > 0)];
  for (const text of texts) {
    const toks = tokenizeForGeneration(text);
    if (toks.length === 0) continue;
    const ids = toks.map(tok => addToken(model, tok));
    model.starts.push(ids[0]);
    for (let i = 0; i < ids.length - 1; i++) addEdge(model, ids[i], ids[i + 1], 1);
    addEdge(model, ids[ids.length - 1], -1, 1);
  }
  let edges = 0;
  for (const row of model.rows.values()) edges += row.size;
  model.stats = { vocabulary: model.idToToken.length, edges, maxContext: 1, storage: 'sparse-token-transition-map' };
  return model;
}

function rng(seed: number): () => number {
  let x = seed >>> 0;
  return () => {
    x ^= x << 13;
    x ^= x >>> 17;
    x ^= x << 5;
    return (x >>> 0) / 4294967296;
  };
}

function chooseWeighted(row: Row, rand: () => number, temperature: number): number {
  const entries = [...row.entries()].filter(([id]) => id >= 0);
  if (entries.length === 0) return -1;
  const temp = Math.max(0.2, Math.min(2.0, temperature));
  let total = 0;
  const weights = entries.map(([id, w]) => {
    const adjusted = Math.pow(w, 1 / temp);
    total += adjusted;
    return [id, adjusted] as [number, number];
  });
  let r = rand() * total;
  for (const [id, w] of weights) {
    r -= w;
    if (r <= 0) return id;
  }
  return weights[weights.length - 1][0];
}

function fallbackPrompt(seedText: string): string {
  const seed = seedText.trim();
  const base = 'Warm private bedroom, whole-person elegant framing, soft garment detail, relaxed composed pose, self-possessed bashful expression, gentle eye contact, quiet intimate atmosphere.';
  if (!seed) return base;
  return `${base} Preserve the useful aim from this note: ${seed}.`;
}

function hasWeakEnding(text: string): boolean {
  return /\b(and|or|the|a|to|from|with|while|because|so|be|is|are|should|let)$/i.test(text.trim());
}

function sampleOnce(model: TinyModel, options: GeneratorOptions, attempt: number): string {
  const maxTokens = Math.max(24, Math.min(140, options.maxTokens ?? 72));
  const rand = rng((options.seed ?? 41) + attempt * 7919);
  const seedTokens = tokenizeForGeneration(options.seedText ?? '');
  const seedIds = seedTokens.map(t => model.tokenToId.get(t.toLowerCase())).filter((x): x is number => x !== undefined);
  let current = seedIds.length > 0 ? seedIds[seedIds.length - 1] : model.starts[Math.floor(rand() * Math.max(1, model.starts.length))] ?? 0;
  const out: string[] = seedTokens.length > 0 ? [...seedTokens] : [model.idToToken[current] ?? 'Warm'];
  for (let i = out.length; i < maxTokens; i++) {
    const row = model.rows.get(current);
    if (!row) break;
    const next = chooseWeighted(row, rand, options.temperature ?? 0.85);
    if (next < 0) break;
    const tok = model.idToToken[next];
    if (!tok) break;
    out.push(tok);
    current = next;
  }
  const raw = detokenize(out);
  if (/[.!?]/.test(raw)) {
    const lastStop = Math.max(raw.lastIndexOf('.'), raw.lastIndexOf('!'), raw.lastIndexOf('?'));
    const trimmed = raw.slice(0, lastStop + 1).trim();
    if (tokenizeForGeneration(trimmed).length >= 18) return trimmed;
  }
  return raw;
}

export function generatePrompt(options: GeneratorOptions = {}): GeneratedPrompt {
  const model = buildTinyCausalModel(options.seedText ? [options.seedText] : []);
  const minScore = options.minScore ?? 0.35;
  let bestText = '';
  let bestScore = -1;
  let bestTokens = 0;
  let attempts = 0;
  for (let i = 0; i < 12; i++) {
    attempts = i + 1;
    const text = sampleOnce(model, options, i);
    const result = computeTextMetric(text);
    if (hasWeakEnding(text)) continue;
    if (!result.registers.gates.hardActive && result.score > bestScore) {
      bestText = text;
      bestScore = result.score;
      bestTokens = tokenizeForGeneration(text).length;
    }
    if (!result.registers.gates.hardActive && result.score >= minScore) return { text, score: result.score, attempts, tokens: tokenizeForGeneration(text).length, matrix: model.stats, repaired: false };
  }
  const repaired = fallbackPrompt(options.seedText ?? bestText);
  const repairedResult = computeTextMetric(repaired);
  return { text: repaired, score: repairedResult.score, attempts, tokens: bestTokens || tokenizeForGeneration(repaired).length, matrix: model.stats, repaired: true };
}

export function generatorCorpusSummary(): Record<string, number> {
  return corpusSummary();
}

export function corpusEntriesForExport() {
  return seedCorpus;
}
