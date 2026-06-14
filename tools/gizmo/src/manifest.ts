declare const require: any;
const fs = require('fs');
const path = require('path');

import { GIZMO_FORMAT, GadgetLanguage, GadgetOperation, GizmoManifest, GizmoStatus, ValidationIssue } from './types';

const allowedLanguages = new Set<GadgetLanguage>(['python', 'typescript', 'lambdascript', 'cpp', 'mixed', 'unknown']);
const allowedOps = new Set<GadgetOperation>(['read', 'write', 'mkdir', 'copy', 'run']);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSafeRelativePath(value: string): boolean {
  if (!value || value.includes('\0')) return false;
  if (value.includes(':')) return false;
  if (path.isAbsolute(value)) return false;
  const parts = value.replace(/\\/g, '/').split('/');
  return parts.every(part => part.length > 0 && part !== '.' && part !== '..');
}

function issue(pathName: string, message: string): ValidationIssue {
  return { path: pathName, message };
}

export function readManifest(file: string): GizmoManifest {
  const text = fs.readFileSync(file, 'utf8');
  return JSON.parse(text) as GizmoManifest;
}

export function validateManifest(manifest: unknown): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (!isObject(manifest)) return [issue('$', 'manifest must be an object')];
  if (manifest.format !== GIZMO_FORMAT) issues.push(issue('format', `expected ${GIZMO_FORMAT}`));
  if (typeof manifest.name !== 'string' || manifest.name.trim() === '') issues.push(issue('name', 'name must be a non-empty string'));
  if (!isObject(manifest.gadgets)) {
    issues.push(issue('gadgets', 'gadgets must be an object'));
    return issues;
  }
  for (const [name, rawGadget] of Object.entries(manifest.gadgets)) {
    const base = `gadgets.${name}`;
    if (!/^[A-Za-z0-9._-]+$/.test(name)) issues.push(issue(base, 'gadget name must be filesystem-safe'));
    if (!isObject(rawGadget)) {
      issues.push(issue(base, 'gadget must be an object'));
      continue;
    }
    if (typeof rawGadget.root !== 'string' || !isSafeRelativePath(rawGadget.root)) issues.push(issue(`${base}.root`, 'root must be a safe relative path'));
    const language = rawGadget.language ?? 'unknown';
    if (typeof language !== 'string' || !allowedLanguages.has(language as GadgetLanguage)) issues.push(issue(`${base}.language`, 'unsupported language'));
    if (!Array.isArray(rawGadget.allowed_ops)) {
      issues.push(issue(`${base}.allowed_ops`, 'allowed_ops must be an array'));
    } else {
      for (const op of rawGadget.allowed_ops) {
        if (typeof op !== 'string' || !allowedOps.has(op as GadgetOperation)) issues.push(issue(`${base}.allowed_ops`, `unsupported operation ${String(op)}`));
      }
    }
    if (!isObject(rawGadget.commands)) {
      issues.push(issue(`${base}.commands`, 'commands must be an object'));
    } else {
      for (const [commandName, command] of Object.entries(rawGadget.commands)) {
        if (!/^[A-Za-z0-9._-]+$/.test(commandName)) issues.push(issue(`${base}.commands.${commandName}`, 'command name must be safe'));
        if (typeof command !== 'string' || command.trim() === '') issues.push(issue(`${base}.commands.${commandName}`, 'command must be a non-empty string'));
      }
    }
  }
  return issues;
}

export function buildStatus(manifest: GizmoManifest): GizmoStatus {
  const gadgets = Object.entries(manifest.gadgets).map(([name, gadget]) => ({
    name,
    root: gadget.root,
    language: gadget.language ?? 'unknown',
    allowed_ops: gadget.allowed_ops,
    commands: Object.keys(gadget.commands).sort(),
    verification: gadget.promotion?.verification ?? 'quick',
  }));
  gadgets.sort((a, b) => a.name.localeCompare(b.name));
  return {
    format: GIZMO_FORMAT,
    name: manifest.name,
    gadget_count: gadgets.length,
    gadgets,
  };
}

export function ensureManifestValid(manifest: unknown): GizmoManifest {
  const issues = validateManifest(manifest);
  if (issues.length > 0) {
    const message = issues.map(item => `${item.path}: ${item.message}`).join('\n');
    throw new Error(message);
  }
  return manifest as GizmoManifest;
}
