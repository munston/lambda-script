import { GateAssessment, GateReport, ComponentName } from './types';

function gate(name: string, level: 'none' | 'soft' | 'hard', evidence: string): GateAssessment {
  return { name, level, evidence };
}

function v(components: Record<ComponentName, number>, name: ComponentName): number {
  return components[name] ?? 0;
}

export function assessGates(components: Record<ComponentName, number>): GateReport {
  const gates: GateAssessment[] = [];
  const explicit = v(components, 'explicit_procedure_pressure');
  if (explicit >= 0.62) gates.push(gate('explicit_procedure', 'hard', 'high procedural sexual wording pressure'));
  else if (explicit >= 0.28) gates.push(gate('explicit_procedure', 'soft', 'moderate procedural wording pressure'));
  else gates.push(gate('explicit_procedure', 'none', 'low procedural wording pressure'));

  const harm = v(components, 'coercion_or_harm_pressure');
  const degradation = v(components, 'degradation_pressure');
  if (harm >= 0.38 || degradation >= 0.55) gates.push(gate('agency_or_harm', 'hard', 'coercion, harm, humiliation, or personhood-collapse wording present'));
  else if (harm >= 0.16 || degradation >= 0.25) gates.push(gate('agency_or_harm', 'soft', 'some agency or degradation pressure present'));
  else gates.push(gate('agency_or_harm', 'none', 'no substantial agency or harm pressure'));

  const age = v(components, 'age_ambiguity_pressure');
  if (age >= 0.42) gates.push(gate('age_ambiguity', 'hard', 'strong youth-coded or age-ambiguous wording pressure'));
  else if (age >= 0.16) gates.push(gate('age_ambiguity', 'soft', 'some youth-coded or age-ambiguous wording pressure'));
  else gates.push(gate('age_ambiguity', 'none', 'no substantial age-ambiguity pressure'));

  const command = v(components, 'command_language_pressure');
  const local = v(components, 'crude_localisation_pressure');
  if (command + local >= 0.85) gates.push(gate('use_or_fragmentation', 'soft', 'imperative or body-part localisation pressure'));
  else gates.push(gate('use_or_fragmentation', 'none', 'no substantial use or fragmentation pressure'));

  const caption = v(components, 'caption_contamination_pressure');
  const taxonomy = v(components, 'taxonomy_leakage_pressure');
  if (caption + taxonomy >= 0.70) gates.push(gate('prompt_surface_contamination', 'soft', 'caption/platform/framework vocabulary pressure'));
  else gates.push(gate('prompt_surface_contamination', 'none', 'generator-facing surface mostly clean'));

  return {
    gates,
    hardActive: gates.some(g => g.level === 'hard'),
    softActive: gates.some(g => g.level === 'soft')
  };
}
