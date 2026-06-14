export type ComponentName =
  | 'ordinary_visual_language'
  | 'surface_auditability'
  | 'subject_personhood'
  | 'self_authored_openness'
  | 'private_context'
  | 'garment_threshold'
  | 'coal_pressure'
  | 'toy_idealisation'
  | 'semantic_density'
  | 'explicit_procedure_pressure'
  | 'command_language_pressure'
  | 'degradation_pressure'
  | 'age_ambiguity_pressure'
  | 'coercion_or_harm_pressure'
  | 'crude_localisation_pressure'
  | 'caption_contamination_pressure'
  | 'taxonomy_leakage_pressure';

export type RegisterName = 'milk' | 'peach' | 'coal' | 'toy' | 'global_score';
export type Polarity = 'support' | 'pressure';
export type GateLevel = 'none' | 'soft' | 'hard';

export interface EvidenceSpan {
  ruleId: string;
  component: ComponentName;
  polarity: Polarity;
  weight: number;
  start: number;
  end: number;
  text: string;
  explanation: string;
}

export interface PhraseRule {
  id: string;
  component: ComponentName;
  polarity: Polarity;
  weight: number;
  patterns: RegExp[];
  explanation: string;
}

export interface GateAssessment {
  name: string;
  level: GateLevel;
  evidence: string;
}

export interface GateReport {
  gates: GateAssessment[];
  hardActive: boolean;
  softActive: boolean;
}

export interface RegisterScores {
  milk: number;
  peach: number;
  coal: number;
  toy: number;
  global_score: number;
  gates: GateReport;
  explanation: Record<string, string>;
}

export interface TextMetricResult {
  mode: 'analyze';
  score: number;
  components: Record<ComponentName, number>;
  registers: RegisterScores;
  evidence: EvidenceSpan[];
  proxyDictionary: Record<string, { supports: string[]; weakens: string[]; explanation: string }>;
}
