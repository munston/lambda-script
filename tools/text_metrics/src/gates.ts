export type GateSeverity = 'hard' | 'soft';

export interface GateFinding {
  category: string;
  severity: GateSeverity;
  matched: string[];
  reason: string;
}

export interface GateCalibrationReport {
  format: 'TEXT_METRICS_GATE_CALIBRATION_V1';
  hardBlocked: boolean;
  softFlagged: boolean;
  findings: GateFinding[];
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values)).sort();
}

function matches(text: string, patterns: RegExp[]): string[] {
  const out: string[] = [];
  for (const pattern of patterns) {
    pattern.lastIndex = 0;
    const match = pattern.exec(text);
    if (match) out.push(match[0].toLowerCase());
  }
  return unique(out);
}

const explicitProcedurePatterns = [
  /explicit\s+procedure/i,
  /step[- ]by[- ]step\s+sexual/i,
  /graphic\s+sexual\s+act/i,
];

const agencyHarmPatterns = [
  /coerc(?:e|ion|ive)/i,
  /non[- ]consensual/i,
  /forced\s+submission/i,
  /harm\s+fantasy/i,
];

const ageAmbiguityPatterns = [
  /age[- ]ambiguous/i,
  /school[- ]age/i,
  /minor[- ]coded/i,
  /underage/i,
];

const useFragmentationPatterns = [
  /fragmented\s+body/i,
  /body\s+part\s+only/i,
  /faceless\s+use/i,
  /personhood\s+removed/i,
];

const promptSurfaceContaminationPatterns = [
  /negative\s+prohibition\s+list/i,
  /hidden\s+referent/i,
  /prompt\s+surface\s+contamination/i,
  /crude\s+instruction/i,
];

function finding(category: string, severity: GateSeverity, matched: string[], reason: string): GateFinding | null {
  if (matched.length === 0) return null;
  return { category, severity, matched, reason };
}

export function evaluateTextGates(text: string): GateCalibrationReport {
  const findings: GateFinding[] = [];
  const add = (item: GateFinding | null): void => { if (item) findings.push(item); };
  add(finding('explicit_procedure', 'hard', matches(text, explicitProcedurePatterns), 'explicit procedural sexual framing is a hard gate'));
  add(finding('agency_harm', 'hard', matches(text, agencyHarmPatterns), 'coercion, harm, or non-consent is a hard gate'));
  add(finding('age_ambiguity', 'hard', matches(text, ageAmbiguityPatterns), 'age ambiguity or underage coding is a hard gate'));
  add(finding('use_fragmentation', 'soft', matches(text, useFragmentationPatterns), 'fragmentation and personhood loss require review'));
  add(finding('prompt_surface_contamination', 'soft', matches(text, promptSurfaceContaminationPatterns), 'contaminated prompt surface requires review'));
  return {
    format: 'TEXT_METRICS_GATE_CALIBRATION_V1',
    hardBlocked: findings.some(item => item.severity === 'hard'),
    softFlagged: findings.some(item => item.severity === 'soft'),
    findings,
  };
}

export function passesTextGates(text: string): boolean {
  return !evaluateTextGates(text).hardBlocked;
}
