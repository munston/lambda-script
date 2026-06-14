declare const require: any;
declare const process: any;
declare const module: any;
const fs = require('fs');
const path = require('path');

import { buildStatus, ensureManifestValid, readManifest, validateManifest } from './manifest';
import { GIZMO_FORMAT, GizmoManifest } from './types';

function usage(): string {
  return `Usage:
  gizmo init <name> --out <file>
  gizmo validate <manifest.json>
  gizmo status <manifest.json>
`;
}

function argValue(args: string[], name: string, fallback?: string): string | undefined {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}

function writeJson(file: string, value: unknown): void {
  const dir = path.dirname(file);
  if (dir && dir !== '.') fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
}

function initManifest(name: string): GizmoManifest {
  return {
    format: GIZMO_FORMAT,
    name,
    gadgets: {},
  };
}

export function runCli(args: string[]): number {
  try {
    const command = args[0];
    if (!command) {
      console.log(usage());
      return 1;
    }
    if (command === 'init') {
      const name = args[1];
      if (!name) throw new Error('missing gizmo name');
      const out = argValue(args, '--out', `${name}.gizmo.json`) ?? `${name}.gizmo.json`;
      writeJson(out, initManifest(name));
      console.log(out);
      return 0;
    }
    if (command === 'validate') {
      const file = args[1];
      if (!file) throw new Error('missing manifest path');
      const manifest = readManifest(file);
      const issues = validateManifest(manifest);
      if (issues.length > 0) {
        console.error(JSON.stringify({ valid: false, issues }, null, 2));
        return 1;
      }
      console.log(JSON.stringify({ valid: true, file }, null, 2));
      return 0;
    }
    if (command === 'status') {
      const file = args[1];
      if (!file) throw new Error('missing manifest path');
      const manifest = ensureManifestValid(readManifest(file));
      console.log(JSON.stringify(buildStatus(manifest), null, 2));
      return 0;
    }
    throw new Error(`unknown command: ${command}`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  process.exitCode = runCli(process.argv.slice(2));
}
