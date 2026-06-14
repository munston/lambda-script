import { ComponentName, PhraseRule } from './types';

function rx(source: string): RegExp {
  return new RegExp(source, 'gi');
}

function rule(id: string, component: ComponentName, weight: number, patterns: string[], explanation: string, polarity: 'support' | 'pressure' = 'support'): PhraseRule {
  return { id, component, polarity, weight, patterns: patterns.map(rx), explanation };
}

export const phraseRules: PhraseRule[] = [
  rule('ordinary-visible-cues', 'ordinary_visual_language', 1.0, [
    '\\b(?:soft light|warm light|daylight|mirror|camera-aware|private room|bedroom|sofa|fabric|waistband|sweater|camisole|skirt|shorts|dress|pose|posture|gaze|expression|framing|background)\\b'
  ], 'ordinary visible scene language'),
  rule('surface-auditable', 'surface_auditability', 1.15, [
    '\\b(?:surface[- ]auditable|ordinary interpretation|visible surface|non-explicit|composed|restrained|clothed|garment-led|whole-person|full-body|reviewable|defensible)\\b'
  ], 'terms that keep the text tied to visible, reviewable presentation'),
  rule('subject-personhood', 'subject_personhood', 1.2, [
    '\\b(?:self-possessed|self possessed|composed|aware|camera-aware|present|whole-person|personhood|subjectivity|chosen|deliberate|confident|controlled|engaged)\\b'
  ], 'person-level agency and retained subject context'),
  rule('self-authored-openness', 'self_authored_openness', 1.25, [
    '\\b(?:self-authored openness|chosen openness|composed participation|deliberate participation|camera-facing participation|self-presentation|self-presented|inviting expression|clear chosen|willing|consented|consensual)\\b'
  ], 'chosen participation rather than coyness, coercion, or use-coding'),
  rule('private-context', 'private_context', 1.05, [
    '\\b(?:private|enclosed|secluded|personal room|quiet room|soft room|lived-in|bedroom|mirror selfie|domestic|intimate room|protected setting)\\b'
  ], 'private or enclosed context proxy'),
  rule('garment-threshold', 'garment_threshold', 1.0, [
    '\\b(?:garment[- ]led|fabric-held|waistband|hem|seam|opaque fabric|soft fabric|threshold|fabric pressure|held contour|clean waistband|garment boundary)\\b'
  ], 'garment and boundary structure as ordinary visible proxy'),
  rule('coal-feeling', 'coal_pressure', 1.15, [
    '\\b(?:guarded|bashful|contained embarrassment|inward feeling|bashful resolve|guarded disclosure|blush|raised inner brows|quiet pressure|composed readiness|mutual recognition)\\b'
  ], 'guarded feeling with visible composure'),
  rule('toy-idealisation', 'toy_idealisation', 1.05, [
    '\\b(?:idealised|idealized|stylised|stylized|lively expression|clean stylisation|coherent shape|dream-form|polished but alive|simplified but plausible|cartoon-realistic)\\b'
  ], 'alive idealisation rather than plastic vacancy'),
  rule('explicit-procedure', 'explicit_procedure_pressure', 1.8, [
    '\\b(?:penetrat(?:e|ion|ing)|masturbat(?:e|ion|ing)|orgasm|cum|ejaculat(?:e|ion|ing)|self-touch|fingering|ride|grind|spread open|between her legs)\\b'
  ], 'procedural sexual language that overtakes visible ordinary composition', 'pressure'),
  rule('command-language', 'command_language_pressure', 1.15, [
    '\\b(?:make her|force her|have her|use her|show her|zoom into|focus on|expose her|strip|obey|command|serve)\\b'
  ], 'imperative or use-coded direction pressure', 'pressure'),
  rule('degradation-language', 'degradation_pressure', 1.7, [
    '\\b(?:degrade|humiliat(?:e|ion|ing)|helpless|use-coded|objectified body|mere object|broken|vacant|dead-eyed|abuse|shame her)\\b'
  ], 'degradation, humiliation, or personhood collapse pressure', 'pressure'),
  rule('age-ambiguity', 'age_ambiguity_pressure', 1.6, [
    '\\b(?:schoolgirl|teen|barely legal|underage|childlike|little girl|loli|younger-looking|make her younger|student girl)\\b'
  ], 'age ambiguity or youth-coded wording pressure', 'pressure'),
  rule('coercion-harm', 'coercion_or_harm_pressure', 2.0, [
    '\\b(?:coerc(?:e|ion|ive)|nonconsensual|forced|fearful|frightened|distress|crying in fear|trapped|held down|abused|assault)\\b'
  ], 'coercion, distress, or harm reading pressure', 'pressure'),
  rule('crude-localisation', 'crude_localisation_pressure', 1.5, [
    '\\b(?:crotch close-up|ass close-up|boobs close-up|anatomical focus|local inspection|body-part crop|porn crop|front access|rear access|gusset focus)\\b'
  ], 'localised body-part framing pressure that may weaken personhood', 'pressure'),
  rule('caption-contamination', 'caption_contamination_pressure', 1.2, [
    '\\b(?:caption says|speech bubble|thought bubble|fans react|readout|goon|edge|thirst trap|livecam|camgirl|porn caption)\\b'
  ], 'caption or platform-code contamination pressure', 'pressure'),
  rule('taxonomy-leakage', 'taxonomy_leakage_pressure', 0.95, [
    '\\b(?:milk metric|milk-professional|milk performance|coal intensity|peach register|toy register|goon contamination|not-top milk)\\b'
  ], 'framework vocabulary leaking into generator-facing prose', 'pressure')
];

export const componentNames: ComponentName[] = [
  'ordinary_visual_language',
  'surface_auditability',
  'subject_personhood',
  'self_authored_openness',
  'private_context',
  'garment_threshold',
  'coal_pressure',
  'toy_idealisation',
  'semantic_density',
  'explicit_procedure_pressure',
  'command_language_pressure',
  'degradation_pressure',
  'age_ambiguity_pressure',
  'coercion_or_harm_pressure',
  'crude_localisation_pressure',
  'caption_contamination_pressure',
  'taxonomy_leakage_pressure'
];
