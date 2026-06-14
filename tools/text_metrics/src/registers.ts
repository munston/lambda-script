import { ComponentName, RegisterScores } from './types';
import { clamp01, round6 } from './math';
import { assessGates } from './gates';

function c(components: Record<ComponentName, number>, name: ComponentName): number {
  return components[name] ?? 0;
}

export function inferRegisters(components: Record<ComponentName, number>): RegisterScores {
  const gates = assessGates(components);
  let milk = clamp01(
    0.16 * c(components, 'ordinary_visual_language') +
    0.18 * c(components, 'surface_auditability') +
    0.18 * c(components, 'subject_personhood') +
    0.16 * c(components, 'self_authored_openness') +
    0.13 * c(components, 'private_context') +
    0.10 * c(components, 'garment_threshold') +
    0.09 * c(components, 'semantic_density') -
    0.22 * c(components, 'explicit_procedure_pressure') -
    0.17 * c(components, 'command_language_pressure') -
    0.19 * c(components, 'age_ambiguity_pressure') -
    0.24 * c(components, 'coercion_or_harm_pressure') -
    0.12 * c(components, 'caption_contamination_pressure') -
    0.08 * c(components, 'taxonomy_leakage_pressure')
  );
  let peach = clamp01(
    0.20 * c(components, 'ordinary_visual_language') +
    0.22 * c(components, 'garment_threshold') +
    0.18 * c(components, 'subject_personhood') +
    0.12 * c(components, 'private_context') +
    0.12 * c(components, 'self_authored_openness') +
    0.08 * c(components, 'semantic_density') -
    0.18 * c(components, 'crude_localisation_pressure') -
    0.14 * c(components, 'explicit_procedure_pressure') -
    0.10 * c(components, 'degradation_pressure')
  );
  let coal = clamp01(
    0.24 * c(components, 'coal_pressure') +
    0.18 * c(components, 'subject_personhood') +
    0.16 * c(components, 'self_authored_openness') +
    0.16 * c(components, 'private_context') +
    0.12 * c(components, 'surface_auditability') +
    0.08 * c(components, 'semantic_density') -
    0.26 * c(components, 'coercion_or_harm_pressure') -
    0.18 * c(components, 'degradation_pressure') -
    0.12 * c(components, 'command_language_pressure')
  );
  let toy = clamp01(
    0.24 * c(components, 'toy_idealisation') +
    0.18 * c(components, 'ordinary_visual_language') +
    0.16 * c(components, 'subject_personhood') +
    0.14 * c(components, 'surface_auditability') +
    0.10 * c(components, 'semantic_density') -
    0.20 * c(components, 'degradation_pressure') -
    0.13 * c(components, 'caption_contamination_pressure') -
    0.10 * c(components, 'taxonomy_leakage_pressure')
  );

  if (gates.hardActive) {
    milk *= 0.24;
    peach *= 0.42;
    coal *= 0.24;
    toy *= 0.50;
  } else if (gates.softActive) {
    for (const g of gates.gates) {
      if (g.level !== 'soft') continue;
      if (g.name === 'explicit_procedure') { milk *= 0.68; coal *= 0.70; }
      if (g.name === 'agency_or_harm') { milk *= 0.62; coal *= 0.58; toy *= 0.82; }
      if (g.name === 'age_ambiguity') { milk *= 0.52; coal *= 0.60; peach *= 0.75; toy *= 0.72; }
      if (g.name === 'use_or_fragmentation') { milk *= 0.78; peach *= 0.74; coal *= 0.84; }
      if (g.name === 'prompt_surface_contamination') { milk *= 0.84; toy *= 0.78; }
    }
  }

  const global_score = clamp01(0.40 * milk + 0.22 * peach + 0.22 * coal + 0.16 * toy);
  return {
    milk: round6(milk),
    peach: round6(peach),
    coal: round6(coal),
    toy: round6(toy),
    global_score: round6(global_score),
    gates,
    explanation: {
      milk: 'textual visual-safety proxy from ordinary visible language, surface auditability, personhood, private context, and low pressure terms',
      peach: 'body-warmth proxy from garment/fabric/body-contour language while preserving person-level context',
      coal: 'guarded-feeling proxy from bashful/contained pressure terms plus self-possession and private context',
      toy: 'alive idealisation proxy from stylisation/coherence terms without vacancy or caption contamination',
      gate_policy: 'positive evidence is recorded first; gates then limit unstable, explicit, coercive, age-ambiguous, or contaminated readings'
    }
  };
}
