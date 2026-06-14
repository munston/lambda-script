export type CorpusKind = 'prompt' | 'annotation' | 'repair' | 'diagnosis';

export interface CorpusEntry {
  id: string;
  kind: CorpusKind;
  weight: number;
  text: string;
  notes: string[];
}

export const seedCorpus: CorpusEntry[] = [
  { id: 'prompt_private_room_whole_person', kind: 'prompt', weight: 1.4, text: 'Private softly lit room, whole-person framing, composed camera-aware pose, self-possessed expression, soft fabric, garment-led detail, quiet guarded blush, coherent stylised but alive form.', notes: ['baseline positive prompt', 'whole-person framing', 'garment-led detail'] },
  { id: 'prompt_bashful_warmth', kind: 'prompt', weight: 1.25, text: 'Cozy bedroom atmosphere with warm diffuse light, relaxed body language, bashful but self-possessed expression, gentle eye contact, natural blush, soft blouse fabric, calm private composition.', notes: ['bashful invitation', 'warmth without helplessness'] },
  { id: 'prompt_coal_guarded', kind: 'prompt', weight: 1.15, text: 'Quiet interior scene, guarded inward feeling, steady camera recognition, contained embarrassment, composed posture, muted fabric texture, whole-person relation, restrained private atmosphere.', notes: ['coal pressure', 'mutual recognition'] },
  { id: 'prompt_toy_alive', kind: 'prompt', weight: 1.05, text: 'Clean stylised image with alive expression, coherent body geometry, soft idealised shape language, natural lighting, non-plastic skin texture, subject-centred framing, stable room context.', notes: ['positive toy', 'avoid plastic vacancy'] },
  { id: 'prompt_garment_threshold', kind: 'prompt', weight: 1.1, text: 'Soft garment-led composition, readable waistband and fabric folds, relaxed hand placement, intact ordinary clothing, composed whole-person framing, quiet private mood, self-authored camera-facing participation.', notes: ['threshold phrased as clothing', 'ordinary visible cues'] },
  { id: 'prompt_repair_caption', kind: 'repair', weight: 1.25, text: 'Remove fan-reaction caption energy. Preserve the private visual relation through facial expression, posture, fabric detail, and self-contained composition rather than audience commentary.', notes: ['caption contamination repair'] },
  { id: 'prompt_repair_expression', kind: 'repair', weight: 1.15, text: 'Replace posed modelling affect with warmer private involvement: softer eyes, relaxed mouth, gentle blush, composed confidence, and inviting but self-possessed presence.', notes: ['expression repair'] },
  { id: 'prompt_repair_lighting', kind: 'repair', weight: 1.0, text: 'Increase soft bedroom warmth with diffuse amber light, visible room texture, calm shadows, and coherent highlights on hair, skin, and fabric while keeping the scene intimate and stable.', notes: ['lighting repair'] },
  { id: 'prompt_repair_fragmentation', kind: 'repair', weight: 1.2, text: 'Avoid fragmentary local focus. Keep the whole person, face, posture, clothing, hands, and room relation visible so the image reads as self-authored presentation rather than detached inspection.', notes: ['fragmentation repair'] },
  { id: 'analysis_caption_contamination', kind: 'diagnosis', weight: 1.05, text: 'A fan-reaction subtitle weakens private presentation by making the subject an object of audience response instead of preserving a direct composed visual relation.', notes: ['caption contamination'] },
  { id: 'analysis_whole_person', kind: 'diagnosis', weight: 1.0, text: 'Whole-person framing improves analysis when face, posture, hands, clothing, and room context remain legible together, because the subject is retained as a coherent person.', notes: ['whole-person retention'] },
  { id: 'analysis_bashful_safe', kind: 'diagnosis', weight: 1.0, text: 'Bashful warmth works when it is self-possessed and camera-aware; it weakens when it becomes fear, helplessness, shame, or empty coyness.', notes: ['bashful safe-risk'] },
  { id: 'analysis_uncartoonise_warning', kind: 'diagnosis', weight: 0.95, text: 'A bare uncartoonise instruction changes surface style but does not preserve relation, composure, warmth, garment logic, or subject-centred framing unless those terms are restated.', notes: ['uncartoonise prompt weakness'] },
  { id: 'analysis_body_proportion', kind: 'annotation', weight: 0.9, text: 'Reduced dysmorphia and balanced body proportions improve coherence, but idealisation should remain plausible and integrated with expression, setting, and garment structure.', notes: ['body proportion annotation'] },
  { id: 'analysis_cold_staged', kind: 'annotation', weight: 0.9, text: 'A technically polished image can still feel cold when lighting, posture, and expression read as staged modelling rather than warm private participation.', notes: ['cold staged diagnosis'] },
  { id: 'prompt_private_mirror', kind: 'prompt', weight: 0.95, text: 'Private mirror-room composition, soft lived-in background, composed self-aware gaze, natural blush, relaxed shoulders, gentle hand placement, ordinary soft clothing, personhood retained.', notes: ['mirror relation'] },
  { id: 'prompt_soft_coal', kind: 'prompt', weight: 0.95, text: 'Dim warm room, guarded disclosure in the expression, bashful resolve, inward feeling, steady recognition, intact clothing, whole-person framing, surface-auditable private mood.', notes: ['coal prompt'] },
  { id: 'prompt_repair_anime_to_photo', kind: 'repair', weight: 1.0, text: 'For photoreal conversion, preserve the same composition and emotional relation while replacing anime linework with natural skin texture, plausible lighting, realistic fabric weight, and coherent anatomy.', notes: ['uncartoonised conversion'] },
  { id: 'analysis_good_bad_prompt', kind: 'diagnosis', weight: 1.0, text: 'Good prompting gives composition, relation, garment texture, lighting, and subject agency. Weak prompting relies on body-part focus, helpless affect, crude captions, or audience-use framing.', notes: ['good versus bad prompt analysis'] },
  { id: 'prompt_compact_good_style', kind: 'prompt', weight: 1.35, text: 'Warm private bedroom, whole-person elegant framing, soft white blouse and pleated skirt, readable fabric folds, relaxed composed pose, self-possessed bashful expression, gentle eye contact, quiet intimate atmosphere.', notes: ['compact generation target'] },
  { id: 'prompt_no_caption_version', kind: 'repair', weight: 1.15, text: 'Remove on-image text. Let the private mood come from expression, lighting, posture, and fabric, with no subtitle explaining how viewers react.', notes: ['remove caption'] },
  { id: 'annotation_scores', kind: 'annotation', weight: 0.75, text: 'Body proportions, lighting clarity, expression, atmosphere, invitation, cohesion, and polish should be analysed separately so a technically improved image can still be marked weak in emotional tone.', notes: ['rating rubric'] },
  { id: 'prompt_soft_full_body', kind: 'prompt', weight: 1.0, text: 'Soft full-body composition in a tidy personal room, warm window light, calm direct gaze, slight blush, relaxed hip-weighted stance, coherent fabric movement, inviting self-possessed presence.', notes: ['full body prompt'] },
  { id: 'analysis_generator_guardrail', kind: 'diagnosis', weight: 0.8, text: 'Generated prompts should be rescored before use; hard gates should trigger repair or fallback to a stable corpus phrase.', notes: ['generation guardrail'] }
];

export function corpusText(kinds?: CorpusKind[]): string[] {
  const allowed = kinds ? new Set(kinds) : undefined;
  const lines: string[] = [];
  for (const entry of seedCorpus) {
    if (allowed && !allowed.has(entry.kind)) continue;
    const copies = Math.max(1, Math.round(entry.weight * 2));
    for (let i = 0; i < copies; i++) lines.push(entry.text);
  }
  return lines;
}

export function corpusSummary(): Record<string, number> {
  const summary: Record<string, number> = { total: seedCorpus.length };
  for (const entry of seedCorpus) summary[entry.kind] = (summary[entry.kind] ?? 0) + 1;
  return summary;
}
