export interface TextStats {
  chars: number;
  words: number;
  sentences: number;
  imperativeMarkers: number;
}

export function normaliseText(text: string): string {
  return text.replace(/\r\n/g, '\n');
}

export function words(text: string): string[] {
  const m = text.toLowerCase().match(/[a-z0-9]+(?:[-'][a-z0-9]+)*/g);
  return m ?? [];
}

export function textStats(text: string): TextStats {
  const ws = words(text);
  const sentences = Math.max(1, (text.match(/[.!?]+/g) ?? []).length);
  const imperativeMarkers = (text.match(/\b(?:make|have|show|focus|zoom|emphasise|emphasize|force|add|remove|hide|expose)\b/gi) ?? []).length;
  return { chars: text.length, words: ws.length, sentences, imperativeMarkers };
}

export function lineCol(text: string, offset: number): { line: number; col: number } {
  const prefix = text.slice(0, offset);
  const line = prefix.split('\n').length;
  const lastNewline = prefix.lastIndexOf('\n');
  return { line, col: offset - lastNewline };
}
