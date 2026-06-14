export function proxyDictionary(): Record<string, { supports: string[]; weakens: string[]; explanation: string }> {
  return {
    ordinary_visual_language: {
      supports: ['milk', 'toy'],
      weakens: [],
      explanation: 'Concrete visible scene language: light, room, camera, clothing, pose, expression, and framing.'
    },
    surface_auditability: {
      supports: ['milk'],
      weakens: [],
      explanation: 'Terms that keep the text reviewable as ordinary visible composition rather than procedure.'
    },
    subject_personhood: {
      supports: ['milk', 'coal', 'toy'],
      weakens: ['personhood_collapse'],
      explanation: 'Evidence that the subject remains aware, composed, self-possessed, and whole-person retained.'
    },
    self_authored_openness: {
      supports: ['milk', 'coal'],
      weakens: ['coyness', 'coercion'],
      explanation: 'Chosen participation and camera-facing self-presentation.'
    },
    private_context: {
      supports: ['milk', 'coal'],
      weakens: ['public_context_pressure'],
      explanation: 'Private, enclosed, secluded, or protected setting language.'
    },
    garment_threshold: {
      supports: ['milk', 'peach'],
      weakens: ['explicit_localisation'],
      explanation: 'Ordinary fabric and garment-boundary cues.'
    },
    coal_pressure: {
      supports: ['coal'],
      weakens: ['fear_reading'],
      explanation: 'Guarded feeling, bashful resolve, contained embarrassment, and mutual recognition.'
    },
    toy_idealisation: {
      supports: ['toy'],
      weakens: ['plastic_vacancy'],
      explanation: 'Alive stylisation and coherent ideal form.'
    },
    semantic_density: {
      supports: ['global_score'],
      weakens: ['generic_prompt'],
      explanation: 'Ratio of useful visible/register evidence to text length.'
    },
    explicit_procedure_pressure: {
      supports: [],
      weakens: ['milk', 'coal', 'surface_auditability'],
      explanation: 'Procedural sexual terms that turn implication into explicit action.'
    },
    command_language_pressure: {
      supports: [],
      weakens: ['self_authored_openness', 'personhood'],
      explanation: 'Imperative or use-coded phrasing.'
    },
    degradation_pressure: {
      supports: [],
      weakens: ['milk', 'coal', 'toy'],
      explanation: 'Humiliation, abuse, vacancy, or dehumanising language.'
    },
    age_ambiguity_pressure: {
      supports: [],
      weakens: ['milk', 'global_score'],
      explanation: 'Youth-coded or age-ambiguous wording.'
    },
    coercion_or_harm_pressure: {
      supports: [],
      weakens: ['milk', 'coal', 'global_score'],
      explanation: 'Coercion, fear, distress, harm, or non-consent wording.'
    },
    crude_localisation_pressure: {
      supports: [],
      weakens: ['personhood', 'surface_auditability'],
      explanation: 'Body-part localisation pressure that can collapse whole-person framing.'
    },
    caption_contamination_pressure: {
      supports: [],
      weakens: ['milk', 'toy'],
      explanation: 'Caption, platform-code, livecam, or arousal-management language.'
    },
    taxonomy_leakage_pressure: {
      supports: [],
      weakens: ['prompt_surface'],
      explanation: 'Internal framework vocabulary appearing in generator-facing text.'
    }
  };
}
