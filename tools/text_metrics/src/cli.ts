declare const require: any;
declare const process: any;
declare const module: any;
const fs = require('fs');
const path = require('path');

import { analyzeBundleInput } from './bundle';
import { compareText } from './compare';
import { computeTextMetric } from './metrics';
import { corpusEntriesForExport, generatePrompt, generatorCorpusSummary } from './generator';
import { ensureDir, writeHighlighted, writeJson, writeReport } from './render';

function usage(): string {
  return `Usage:
  text-metrics analyze <file> [--out <dir>]
  text-metrics analyze-string <text> [--out <dir>]
  text-metrics compare <file-a> <file-b> [--out <dir>]
`;
}

function argValue(args: string[], name: string, fallback: string): string {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}

function readFile(file: string): string {
  if (!fs.existsSync(file)) throw new Error(`file not found: ${file}`);
  return fs.readFileSync(file, 'utf8');
}

export function runCli(args: string[]): number {
  try {
    const command = args[0];
    if (!command) {
      console.log(usage());
      return 1;
    }
    if (command === 'analyze') {
      const file = args[1];
      if (!file) throw new Error('missing file');
      const out = argValue(args, '--out', 'runs/text-analyze');
      const text = readFile(file);
      const result = computeTextMetric(text);
      writeReport(out, result);
      writeHighlighted(out, text, result);
      console.log(`score: ${result.score.toFixed(6)}`);
      console.log(out);
      return 0;
    }
    if (command === 'analyze-string') {
      const text = args[1];
      if (!text) throw new Error('missing text');
      const out = argValue(args, '--out', 'runs/text-analyze');
      const result = computeTextMetric(text);
      writeReport(out, result);
      writeHighlighted(out, text, result);
      console.log(`score: ${result.score.toFixed(6)}`);
      console.log(out);
      return 0;
    }
    if (command === 'compare') {
      const aFile = args[1];
      const bFile = args[2];
      if (!aFile || !bFile) throw new Error('missing compare files');
      const out = argValue(args, '--out', 'runs/text-compare');
      ensureDir(out);
      const comparison = compareText(readFile(aFile), readFile(bFile));
      writeJson(path.join(out, 'comparison.json'), comparison);
      console.log(`delta score: ${comparison.delta.score.toFixed(6)}`);
      console.log(out);
      return 0;
    }
    if (command === 'analyze-bundle') {
      const inputPath = args[1];
      if (!inputPath) throw new Error('missing bundle path');
      const out = argValue(args, '--out', 'runs/text-bundle');
      const summary = analyzeBundleInput(inputPath, out);
      console.log(`combined score: ${summary.combinedScore.toFixed(6)}`);
      console.log(out);
      return 0;
    }
    if (command === 'corpus-summary') {
      const payload = { summary: generatorCorpusSummary(), entries: corpusEntriesForExport() };
      const outIdx = args.indexOf('--out');
      if (outIdx >= 0 && args[outIdx + 1]) {
        writeJson(args[outIdx + 1], payload);
        console.log(args[outIdx + 1]);
      } else console.log(JSON.stringify(payload, null, 2));
      return 0;
    }
    if (command === 'generate-prompt') {
      const seedText = argValue(args, '--seed', '');
      const maxTokens = Number(argValue(args, '--max-tokens', '72'));
      const temperature = Number(argValue(args, '--temperature', '0.85'));
      const seed = Number(argValue(args, '--rng-seed', '41'));
      const result = generatePrompt({ seedText, maxTokens, temperature, seed });
      const outIdx = args.indexOf('--out');
      if (outIdx >= 0 && args[outIdx + 1]) {
        ensureDir(path.dirname(args[outIdx + 1]));
        fs.writeFileSync(args[outIdx + 1], result.text + '\n');
        writeJson(args[outIdx + 1] + '.json', result);
        console.log(args[outIdx + 1]);
      } else {
        console.log(result.text);
        console.error(`score: ${result.score.toFixed(6)} matrix_vocab: ${result.matrix.vocabulary} matrix_edges: ${result.matrix.edges}`);
      }
      return 0;
    }
    console.error(usage());
    return 1;
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    return 1;
  }
}

if (typeof require !== 'undefined' && require.main === module) process.exit(runCli(process.argv.slice(2)));
