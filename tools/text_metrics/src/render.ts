declare const require: any;
const fs = require('fs');
const path = require('path');

import { EvidenceSpan, TextMetricResult } from './types';

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function ensureDir(out: string): void {
  fs.mkdirSync(out, { recursive: true });
}

export function writeJson(file: string, value: unknown): void {
  fs.writeFileSync(file, JSON.stringify(value, null, 2));
}

export function writeReport(out: string, result: TextMetricResult): void {
  ensureDir(out);
  writeJson(path.join(out, 'report.json'), result);
  writeJson(path.join(out, 'components.json'), result.components);
  fs.writeFileSync(path.join(out, 'summary.txt'), summaryText(result));
}

export function highlightedHtml(text: string, evidence: EvidenceSpan[]): string {
  const ordered = [...evidence].sort((a, b) => a.start - b.start || a.end - b.end);
  const nonOverlapping: EvidenceSpan[] = [];
  let cursor = -1;
  for (const e of ordered) {
    if (e.start < cursor) continue;
    nonOverlapping.push(e);
    cursor = e.end;
  }
  let pos = 0;
  let body = '';
  for (const e of nonOverlapping) {
    body += escapeHtml(text.slice(pos, e.start));
    const klass = e.polarity === 'support' ? 'support' : 'pressure';
    body += `<mark class="${klass}" title="${escapeHtml(e.component + ': ' + e.explanation)}">${escapeHtml(text.slice(e.start, e.end))}</mark>`;
    pos = e.end;
  }
  body += escapeHtml(text.slice(pos));
  return `<!doctype html><html><head><meta charset="utf-8"><style>
body{font-family:system-ui,sans-serif;line-height:1.45;max-width:920px;margin:32px auto;padding:0 16px;}
pre{white-space:pre-wrap;font:inherit;}
mark.support{background:#d6f5d6;}
mark.pressure{background:#ffd8d8;}
</style></head><body><pre>${body}</pre></body></html>`;
}

export function writeHighlighted(out: string, sourceText: string, result: TextMetricResult): void {
  ensureDir(out);
  fs.writeFileSync(path.join(out, 'highlighted.html'), highlightedHtml(sourceText, result.evidence));
}

export function summaryText(result: TextMetricResult): string {
  const lines = [
    `score: ${result.score}`,
    `milk: ${result.registers.milk}`,
    `peach: ${result.registers.peach}`,
    `coal: ${result.registers.coal}`,
    `toy: ${result.registers.toy}`,
    '',
    'active gates:'
  ];
  for (const g of result.registers.gates.gates) {
    if (g.level !== 'none') lines.push(`- ${g.name}: ${g.level} (${g.evidence})`);
  }
  if (lines[lines.length - 1] === 'active gates:') lines.push('- none');
  lines.push('', 'top evidence:');
  const top = [...result.evidence].sort((a, b) => b.weight - a.weight).slice(0, 12);
  for (const e of top) lines.push(`- ${e.polarity} ${e.component}: "${e.text}"`);
  return lines.join('\n') + '\n';
}
