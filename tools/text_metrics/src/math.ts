export function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

export function saturate(weightedCount: number, scale: number): number {
  if (weightedCount <= 0) return 0;
  return clamp01(1 - Math.exp(-weightedCount / Math.max(scale, 1e-9)));
}

export function round6(x: number): number {
  return Math.round(x * 1_000_000) / 1_000_000;
}
