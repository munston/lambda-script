import { EvidenceSpan, PhraseRule } from './types';

export function collectEvidence(text: string, rules: PhraseRule[]): EvidenceSpan[] {
  const out: EvidenceSpan[] = [];
  for (const r of rules) {
    for (const pattern of r.patterns) {
      pattern.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = pattern.exec(text)) !== null) {
        const matched = m[0];
        out.push({
          ruleId: r.id,
          component: r.component,
          polarity: r.polarity,
          weight: r.weight,
          start: m.index,
          end: m.index + matched.length,
          text: matched,
          explanation: r.explanation
        });
        if (matched.length === 0) pattern.lastIndex++;
      }
    }
  }
  out.sort((a, b) => a.start - b.start || b.weight - a.weight);
  return out;
}
