declare const require: any;
declare const process: any;
declare const module: any;
const fs = require('fs');
const path = require('path');

import { buildProvisionPlan, buildStatus, ensureManifestValid, readManifest, validateManifest } from './manifest';
import { buildGadgetCommandPlan, buildImportedCommandPlan, executeCommandPlan, parseArgPairs } from './runner';
import { GIZMO_FORMAT, GizmoManifest } from './types';

function usage(): string {
  return `Usage:
  gizmo init <name> --out <file>
  gizmo validate <manifest.json>
  gizmo status <manifest.json>
  gizmo branches <manifest.json>
  gizmo provision-plan <manifest.json> [--out <file>]
  gizmo call <manifest.json> <gadget> <command> [--arg name=value ...] [--exec|--exec=true|--exec=false]
  gizmo import-call <manifest.json> <import> <command> [--exec=false]
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

function printBranches(manifest: GizmoManifest): void {
  const status = buildStatus(manifest);
  console.log(`gizmo ${status.name}`);
  for (const gadget of status.gadgets) {
    console.log(`gadget ${gadget.name}`);
    console.log(`  target_ref: ${gadget.target_ref ?? 'n/a'}`);
    console.log(`  integration_branch: ${gadget.integration_branch ?? 'n/a'}`);
    console.log(`  agent_branch_template: ${gadget.agent_branch_template ?? 'n/a'}`);
  }
  for (const item of status.imports) {
    console.log(`import ${item.name}`);
    console.log(`  from: ${item.from_gizmo}/${item.from_gadget}`);
    console.log(`  target_ref: ${item.target_ref ?? 'n/a'}`);
    console.log(`  mode: ${item.mode}`);
    console.log(`  write_policy: ${item.write_policy ?? 'n/a'}`);
  }
}

function parseExecOption(item: string): boolean {
  if (item === '--exec') return true;
  const prefix = '--exec=';
  if (!item.startsWith(prefix)) throw new Error(`invalid exec option: ${item}`);
  const value = item.slice(prefix.length);
  if (value === 'true') return true;
  if (value === 'false') return false;
  throw new Error(`invalid exec option value for --exec: ${value}`);
}

function collectCallArgs(args: string[]): { execute: boolean; pairs: string[] } {
  const pairs: string[] = [];
  let execute = false;
  for (let i = 0; i < args.length; i += 1) {
    const item = args[i];
    if (item === '--exec' || item.startsWith('--exec=')) {
      execute = parseExecOption(item);
      continue;
    }
    if (item === '--arg') {
      const value = args[i + 1];
      if (!value) throw new Error('missing value after --arg');
      pairs.push(value);
      i += 1;
      continue;
    }
    throw new Error(`unknown call option: ${item}`);
  }
  return { execute, pairs };
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
    if (command === 'branches') {
      const file = args[1];
      if (!file) throw new Error('missing manifest path');
      const manifest = ensureManifestValid(readManifest(file));
      printBranches(manifest);
      return 0;
    }
    if (command === 'provision-plan') {
      const file = args[1];
      if (!file) throw new Error('missing manifest path');
      const out = argValue(args, '--out');
      const manifest = ensureManifestValid(readManifest(file));
      const plan = buildProvisionPlan(manifest);
      if (out) {
        writeJson(out, plan);
        console.log(out);
      } else {
        console.log(JSON.stringify(plan, null, 2));
      }
      return 0;
    }
    if (command === 'call') {
      const file = args[1];
      const gadget = args[2];
      const commandName = args[3];
      if (!file || !gadget || !commandName) throw new Error('usage: gizmo call <manifest.json> <gadget> <command> [--arg name=value ...] [--exec|--exec=true|--exec=false]');
      const callArgs = collectCallArgs(args.slice(4));
      const manifest = ensureManifestValid(readManifest(file));
      const plan = buildGadgetCommandPlan(manifest, gadget, commandName, parseArgPairs(callArgs.pairs), callArgs.execute);
      console.log(JSON.stringify(plan, null, 2));
      return executeCommandPlan(plan);
    }
    if (command === 'import-call') {
      const file = args[1];
      const importName = args[2];
      const commandName = args[3];
      if (!file || !importName || !commandName) throw new Error('usage: gizmo import-call <manifest.json> <import> <command> [--exec=false]');
      const callArgs = collectCallArgs(args.slice(4));
      if (callArgs.execute) throw new Error('imported command execution is not implemented');
      if (callArgs.pairs.length > 0) throw new Error('imported command arguments are not implemented');
      const manifest = ensureManifestValid(readManifest(file));
      const plan = buildImportedCommandPlan(manifest, importName, commandName);
      console.log(JSON.stringify(plan, null, 2));
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
