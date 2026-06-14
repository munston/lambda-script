declare const require: any;
const child_process = require('child_process');

import { ensureManifestValid } from './manifest';
import { GIZMO_COMMAND_PLAN_FORMAT, GizmoCommandPlan, GizmoManifest } from './types';

const placeholderPattern = /\{([A-Za-z_][A-Za-z0-9_-]*)\}/g;
const safeArgPattern = /^[^\0\r\n\"&|<>^%]+$/;

function unique(values: string[]): string[] {
  return Array.from(new Set(values)).sort();
}

function placeholders(template: string): string[] {
  const found: string[] = [];
  let match: RegExpExecArray | null;
  placeholderPattern.lastIndex = 0;
  while ((match = placeholderPattern.exec(template)) !== null) found.push(match[1]);
  return unique(found);
}

function quoteArg(value: string): string {
  if (!safeArgPattern.test(value)) throw new Error(`unsafe command argument: ${value}`);
  return `"${value}"`;
}

function renderTemplate(template: string, args: Record<string, string>): string {
  return template.replace(placeholderPattern, (_full, name: string) => quoteArg(args[name]));
}

export function parseArgPairs(values: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const item of values) {
    const index = item.indexOf('=');
    if (index <= 0) throw new Error(`expected --arg name=value, got: ${item}`);
    const name = item.slice(0, index);
    const value = item.slice(index + 1);
    if (!/^[A-Za-z_][A-Za-z0-9_-]*$/.test(name)) throw new Error(`unsafe argument name: ${name}`);
    if (value.length === 0) throw new Error(`empty argument value for ${name}`);
    out[name] = value;
  }
  return out;
}

export function buildGadgetCommandPlan(manifestInput: unknown, gadgetName: string, commandName: string, args: Record<string, string>, execute: boolean): GizmoCommandPlan {
  const manifest = ensureManifestValid(manifestInput) as GizmoManifest;
  const gadget = manifest.gadgets[gadgetName];
  if (!gadget) throw new Error(`unknown gadget: ${gadgetName}`);
  const template = gadget.commands[commandName];
  if (!template) throw new Error(`unknown command for gadget ${gadgetName}: ${commandName}`);

  const required = placeholders(template);
  const supplied = Object.keys(args).sort();
  const missing = required.filter(name => args[name] === undefined);
  const unused = supplied.filter(name => !required.includes(name));
  if (missing.length > 0) throw new Error(`missing command args: ${missing.join(', ')}`);
  if (unused.length > 0) throw new Error(`unused command args: ${unused.join(', ')}`);

  return {
    format: GIZMO_COMMAND_PLAN_FORMAT,
    gizmo: manifest.name,
    scope: 'gadget',
    name: gadgetName,
    command: commandName,
    template,
    rendered: renderTemplate(template, args),
    args,
    cwd: '.',
    execute,
    missing_args: missing,
    unused_args: unused,
  };
}

export function executeCommandPlan(plan: GizmoCommandPlan): number {
  if (!plan.execute) return 0;
  const proc = child_process.spawnSync(plan.rendered, {
    cwd: plan.cwd,
    shell: true,
    stdio: 'inherit',
  });
  if (typeof proc.status === 'number') return proc.status;
  return proc.error ? 1 : 0;
}
