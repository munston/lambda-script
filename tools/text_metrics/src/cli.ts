declare const require: any;
declare const process: any;
declare const module: any;

import { defaultParametricDemo } from './parametric';
import { defaultImageParametricDemo } from './image_parametric';
import { backendVersion, supportedExtensions } from './native';

function usage(): string {
  return [
    'Usage:',
    '  text-metrics version',
    '  text-metrics extensions',
    '  text-metrics parametric-demo --out <dir>',
    '  text-metrics image-parametric-demo --out <dir> [image-or-feature-files...]'
  ].join('\n');
}

function argValue(args: string[], name: string, fallback: string): string {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}

function positionalAfterCommand(args: string[]): string[] {
  const out: string[] = [];
  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--out') { i++; continue; }
    if (args[i].startsWith('--')) continue;
    out.push(args[i]);
  }
  return out;
}

export function runCli(args: string[]): number {
  try {
    const command = args[0];
    if (!command) {
      console.log(usage());
      return 1;
    }
    if (command === 'version') {
      console.log(backendVersion());
      return 0;
    }
    if (command === 'extensions') {
      console.log(supportedExtensions());
      return 0;
    }
    if (command === 'parametric-demo') {
      const outDir = argValue(args, '--out', 'runs/parametric-demo');
      const result = defaultParametricDemo(outDir);
      console.log(JSON.stringify(result, null, 2));
      return 0;
    }
    if (command === 'image-parametric-demo') {
      const outDir = argValue(args, '--out', 'runs/image-parametric-demo');
      const images = positionalAfterCommand(args);
      const result = defaultImageParametricDemo(outDir, images);
      console.log(JSON.stringify(result, null, 2));
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
