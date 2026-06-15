declare const require: any;
declare const process: any;
declare const module: any;

import { defaultImageParametricDemo } from './image_parametric';
import { analyzeImageToDir, backendVersion, supportedExtensions } from './native';

function usage(): string {
  return [
    'Usage:',
    '  image-metrics version',
    '  image-metrics extensions',
    '  image-metrics analyze <image> --out <dir>',
    '  image-metrics image-parametric-demo --out <dir> [image-or-feature-files...]'
  ].join('\n');
}

function argValue(args: string[], name: string, fallback: string): string {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}

function positional(args: string[], start = 1): string[] {
  const out: string[] = [];
  for (let i = start; i < args.length; i++) {
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
    if (command === 'analyze') {
      const images = positional(args, 1);
      if (images.length < 1) throw new Error('analyze requires an image path');
      const outDir = argValue(args, '--out', 'runs/image-analyze');
      const result = analyzeImageToDir({ imagePath: images[0], outDir });
      console.log(JSON.stringify(result, null, 2));
      return 0;
    }
    if (command === 'image-parametric-demo') {
      const outDir = argValue(args, '--out', 'runs/image-parametric-demo');
      const images = positional(args, 1);
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
