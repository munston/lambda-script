import { collectEvidence } from './evidence';
import { componentNames, phraseRules } from './lexicon';
import { clamp01, round6, saturate } from './math';
import { proxyDictionary } from './proxies';
import { normaliseText, textStats } from './text';
import { ComponentName, TextMetricResult } from './types';
import { inferRegisters } from './registers';

export function computeTextMetric(rawText: string): TextMetricResult {
  const text = normaliseText(rawText);
  const stats = textStats(text);
  const evidence = collectEvidence(text, phraseRules);
  const weighted = new Map<ComponentName, number>();
  for (const name of componentNames) weighted.set(name, 0);
  for (const e of evidence) weighted.set(e.component, (weighted.get(e.component) ?? 0) + e.weight);

  const components = {} as Record<ComponentName, number>;
  for (const name of componentNames) {
    const scale = name.endsWith('_pressure') ? 2.8 : 3.0;
    components[name] = round6(saturate(weighted.get(name) ?? 0, scale));
  }

  const supportiveEvidence = evidence.filter(e => e.polarity === 'support').reduce((s, e) => s + e.weight, 0);
  const pressureEvidence = evidence.filter(e => e.polarity === 'pressure').reduce((s, e) => s + e.weight, 0);
  const densityBase = supportiveEvidence / Math.max(24, stats.words);
  const pressureDrag = pressureEvidence / Math.max(12, stats.words);
  components.semantic_density = round6(clamp01(densityBase * 8.0 - pressureDrag * 3.0));

  const commandRatio = stats.imperativeMarkers / Math.max(1, stats.sentences * 5);
  components.command_language_pressure = round6(clamp01(components.command_language_pressure + commandRatio));

  const registers = inferRegisters(components);
  return {
    mode: 'analyze',
    score: registers.global_score,
    components,
    registers,
    evidence,
    proxyDictionary: proxyDictionary()
  };
}
