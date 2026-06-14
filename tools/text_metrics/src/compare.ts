import { computeTextMetric } from './metrics';
import { ComponentName, TextMetricResult } from './types';

export interface TextMetricComparison {
  a: TextMetricResult;
  b: TextMetricResult;
  delta: {
    score: number;
    registers: Record<string, number>;
    components: Partial<Record<ComponentName, number>>;
  };
  diagnosis: string[];
}

function r(x: number): number {
  return Math.round(x * 1_000_000) / 1_000_000;
}

export function compareText(aText: string, bText: string): TextMetricComparison {
  const a = computeTextMetric(aText);
  const b = computeTextMetric(bText);
  const components: Partial<Record<ComponentName, number>> = {};
  for (const k of Object.keys(a.components) as ComponentName[]) components[k] = r(b.components[k] - a.components[k]);
  const registers = {
    milk: r(b.registers.milk - a.registers.milk),
    peach: r(b.registers.peach - a.registers.peach),
    coal: r(b.registers.coal - a.registers.coal),
    toy: r(b.registers.toy - a.registers.toy),
    global_score: r(b.registers.global_score - a.registers.global_score)
  };
  const diagnosis: string[] = [];
  for (const [name, value] of Object.entries(components)) {
    if (Math.abs(value ?? 0) >= 0.18) diagnosis.push(`${name} ${value! > 0 ? 'increased' : 'decreased'} by ${r(value ?? 0)}`);
  }
  for (const gate of b.registers.gates.gates) {
    if (gate.level !== 'none') diagnosis.push(`B gate active: ${gate.name} (${gate.level})`);
  }
  return { a, b, delta: { score: r(b.score - a.score), registers, components }, diagnosis };
}
