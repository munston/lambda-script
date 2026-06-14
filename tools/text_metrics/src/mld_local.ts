export interface LocalInterrogationConfig {
  seed: number;
  stepSize: number;
  steps?: number;
  lower?: number;
  upper?: number;
  maximize?: boolean;
  uphillTolerance?: number;
}

export interface LocalInterrogationSample {
  step: number;
  accepted: boolean;
  value: number;
  delta: number;
}

export interface LocalInterrogationResult {
  baseValue: number;
  terminalValue: number;
  acceptedSteps: number;
  evaluations: number;
  witness: number[];
  normalizedWitness: number[];
  samples: LocalInterrogationSample[];
}

class XorShift32 {
  private x: number;
  constructor(seed: number) { this.x = seed | 0 || 1357913579; }
  nextU32(): number { let x = this.x | 0; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; this.x = x | 0; return this.x >>> 0; }
  next(): number { return this.nextU32() / 4294967296; }
  normal(): number {
    let u = 0, v = 0;
    while (u <= 1e-12) u = this.next();
    while (v <= 1e-12) v = this.next();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
}

function clamp(x: number, lo: number, hi: number): number { return Math.max(lo, Math.min(hi, x)); }
function norm(xs: number[]): number { return Math.sqrt(xs.reduce((s, x) => s + x * x, 0)); }
function normalize(xs: number[]): number[] { const n = norm(xs); return n <= 1e-12 ? xs.map(() => 0) : xs.map(x => x / n); }

function randomUnitVector(k: number, rng: XorShift32): number[] {
  const v = Array.from({ length: k }, () => rng.normal());
  return normalize(v);
}

export function localInterrogationWitness(
  point: number[],
  objective: (x: number[]) => number,
  config: LocalInterrogationConfig
): LocalInterrogationResult {
  const k = point.length;
  const lower = config.lower ?? -Infinity;
  const upper = config.upper ?? Infinity;
  const stepCount = config.steps ?? Math.max(1, Math.ceil(Math.sqrt(k)));
  const maximize = config.maximize ?? true;
  const tol = config.uphillTolerance ?? 0;
  const rng = new XorShift32(config.seed);
  const baseValue = objective(point.slice());
  let current = point.slice();
  let currentValue = baseValue;
  let evaluations = 1;
  let acceptedSteps = 0;
  const witness = point.map(() => 0);
  const samples: LocalInterrogationSample[] = [];
  for (let step = 0; step < stepCount; step++) {
    const dir = randomUnitVector(k, rng);
    const trial = current.map((v, i) => clamp(v + config.stepSize * dir[i], lower, upper));
    const value = objective(trial);
    evaluations++;
    const signedDelta = maximize ? value - currentValue : currentValue - value;
    for (let i = 0; i < k; i++) witness[i] += (signedDelta / Math.max(1e-12, config.stepSize)) * dir[i];
    const accepted = signedDelta >= tol;
    if (accepted) {
      current = trial;
      currentValue = value;
      acceptedSteps++;
    }
    samples.push({ step, accepted, value, delta: signedDelta });
  }
  return {
    baseValue,
    terminalValue: currentValue,
    acceptedSteps,
    evaluations,
    witness,
    normalizedWitness: normalize(witness),
    samples
  };
}

export function localInterrogationGradientStep(
  point: number[],
  objective: (x: number[]) => number,
  config: LocalInterrogationConfig,
  learningRate: number
): { next: number[]; interrogation: LocalInterrogationResult } {
  const interrogation = localInterrogationWitness(point, objective, config);
  const lower = config.lower ?? -Infinity;
  const upper = config.upper ?? Infinity;
  const direction = interrogation.normalizedWitness;
  const next = point.map((v, i) => clamp(v + learningRate * direction[i], lower, upper));
  return { next, interrogation };
}
