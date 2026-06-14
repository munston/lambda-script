declare const require: any;
const fs = require('fs');
const path = require('path');

import { GIZMO_FORMAT, GadgetLanguage, GadgetOperation, GizmoManifest, GizmoStatus, ValidationIssue } from './types';

const allowedLanguages = new Set<GadgetLanguage>(['python', 'typescript', 'lambdascript', 'cpp', 'mixed', 'unknown']);
const allowedOps = new Set<GadgetOperation>(['read', 'write', 'mkdir', 'copy', 'run']);
const safeName = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const safeCommandName = /^[A-Za-z0-9._-]+$/;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeRelPath(value: string): string {
  const raw = value.replace(/\\/g, '/').replace(/\/+/g, '/');
  if (raw === '.') return raw;
  return raw.replace(/\/+$/g, '');
}

function isSafeRelativePath(value: string): boolean {
  if (!value || value.includes('\0')) return false;
  if (value.includes(':')) return false;
  if (path.isAbsolute(value)) return false;
  const normal = normalizeRelPath(value);
  if (normal === '.') return true;
  const parts = normal.split('/');
  return parts.every(part => part.length > 0 && part !== '.' && part !== '..');
}

function isSafeRef(value: string): boolean {
  if (!value || value.includes('\0')) return false;
  if (value.includes('..') || value.includes(' ') || value.includes('~') || value.includes('^') || value.includes(':')) return false;
  if (value.startsWith('/') || value.endsWith('/') || value.includes('//')) return false;
  return /^[A-Za-z0-9._/{}/-]+$/.test(value);
}

function issue(pathName: string, message: string): ValidationIssue {
  return { path: pathName, message };
}

function validateCommandMap(base: string, value: unknown, issues: ValidationIssue[]): void {
  if (!isObject(value)) {
    issues.push(issue(base, 'commands must be an object'));
    return;
  }
  for (const [commandName, command] of Object.entries(value)) {
    if (!safeCommandName.test(commandName)) issues.push(issue(`${base}.${commandName}`, 'command name must be safe'));
    if (typeof command !== 'string' || command.trim() === '') issues.push(issue(`${base}.${commandName}`, 'command must be a non-empty string'));
  }
}

function validateAllowedOps(base: string, value: unknown, issues: ValidationIssue[]): void {
  if (value === undefined) return;
  if (!Array.isArray(value)) {
    issues.push(issue(base, 'allowed_ops must be an array when present'));
    return;
  }
  for (const op of value) {
    if (typeof op !== 'string' || !allowedOps.has(op as GadgetOperation)) issues.push(issue(base, `unsupported operation ${String(op)}`));
  }
}

function validateStringArray(base: string, value: unknown, issues: ValidationIssue[], itemCheck?: (value: string) => boolean, itemMessage?: string): void {
  if (!Array.isArray(value)) {
    issues.push(issue(base, 'must be an array'));
    return;
  }
  value.forEach((item, index) => {
    if (typeof item !== 'string' || item.trim() === '') {
      issues.push(issue(`${base}.${index}`, 'must be a non-empty string'));
      return;
    }
    if (itemCheck && !itemCheck(item)) issues.push(issue(`${base}.${index}`, itemMessage ?? 'invalid string'));
  });
}

function validateVerificationProfiles(base: string, value: unknown, issues: ValidationIssue[]): void {
  if (value === undefined) return;
  if (!isObject(value)) {
    issues.push(issue(base, 'verification_profiles must be an object when present'));
    return;
  }
  for (const [name, commands] of Object.entries(value)) {
    if (!safeCommandName.test(name)) issues.push(issue(`${base}.${name}`, 'profile name must be safe'));
    validateStringArray(`${base}.${name}`, commands, issues);
  }
}

function validateGadget(base: string, rawGadget: Record<string, unknown>, issues: ValidationIssue[]): void {
  if (typeof rawGadget.root !== 'string' || !isSafeRelativePath(rawGadget.root)) issues.push(issue(`${base}.root`, 'root must be a safe relative path'));
  const language = rawGadget.language ?? 'unknown';
  if (typeof language !== 'string' || !allowedLanguages.has(language as GadgetLanguage)) issues.push(issue(`${base}.language`, 'unsupported language'));
  validateAllowedOps(`${base}.allowed_ops`, rawGadget.allowed_ops, issues);
  validateCommandMap(`${base}.commands`, rawGadget.commands, issues);
  if (rawGadget.target_ref !== undefined && (typeof rawGadget.target_ref !== 'string' || !isSafeRef(rawGadget.target_ref))) issues.push(issue(`${base}.target_ref`, 'target_ref must be a safe git ref'));
  if (rawGadget.integration_branch !== undefined && (typeof rawGadget.integration_branch !== 'string' || !isSafeRef(rawGadget.integration_branch))) issues.push(issue(`${base}.integration_branch`, 'integration_branch must be a safe git ref'));
  if (rawGadget.agent_branch_template !== undefined) {
    if (typeof rawGadget.agent_branch_template !== 'string' || !rawGadget.agent_branch_template.includes('{agent}') || !isSafeRef(rawGadget.agent_branch_template)) issues.push(issue(`${base}.agent_branch_template`, 'agent_branch_template must be a safe ref template containing {agent}'));
  }
  if (rawGadget.owned_paths !== undefined) validateStringArray(`${base}.owned_paths`, rawGadget.owned_paths, issues, isSafeRelativePath, 'owned path must be safe and relative');
  validateVerificationProfiles(`${base}.verification_profiles`, rawGadget.verification_profiles, issues);
  if (rawGadget.promotion !== undefined) {
    if (!isObject(rawGadget.promotion)) {
      issues.push(issue(`${base}.promotion`, 'promotion must be an object when present'));
    } else {
      const promotion = rawGadget.promotion;
      if (promotion.target !== undefined && (typeof promotion.target !== 'string' || !isSafeRef(promotion.target))) issues.push(issue(`${base}.promotion.target`, 'promotion target must be a safe git ref'));
      if (promotion.verification !== undefined && (typeof promotion.verification !== 'string' || promotion.verification.trim() === '')) issues.push(issue(`${base}.promotion.verification`, 'promotion verification must be a non-empty string'));
    }
  }
}

function validateImports(imports: unknown, issues: ValidationIssue[]): void {
  if (imports === undefined) return;
  if (!isObject(imports)) {
    issues.push(issue('imports', 'imports must be an object when present'));
    return;
  }
  for (const [name, rawImport] of Object.entries(imports)) {
    const base = `imports.${name}`;
    if (!safeName.test(name)) issues.push(issue(base, 'import name must be filesystem-safe'));
    if (!isObject(rawImport)) {
      issues.push(issue(base, 'import must be an object'));
      continue;
    }
    if (typeof rawImport.from_gizmo !== 'string' || !safeName.test(rawImport.from_gizmo)) issues.push(issue(`${base}.from_gizmo`, 'from_gizmo must be a safe name'));
    if (typeof rawImport.from_gadget !== 'string' || !safeName.test(rawImport.from_gadget)) issues.push(issue(`${base}.from_gadget`, 'from_gadget must be a safe name'));
    if (typeof rawImport.mount !== 'string' || !isSafeRelativePath(rawImport.mount)) issues.push(issue(`${base}.mount`, 'mount must be a safe relative path'));
    if (typeof rawImport.mode !== 'string' || rawImport.mode.trim() === '') issues.push(issue(`${base}.mode`, 'mode must be a non-empty string'));
    if (rawImport.target_ref !== undefined && (typeof rawImport.target_ref !== 'string' || !isSafeRef(rawImport.target_ref))) issues.push(issue(`${base}.target_ref`, 'target_ref must be a safe git ref'));
    if (rawImport.allowed_commands !== undefined) validateStringArray(`${base}.allowed_commands`, rawImport.allowed_commands, issues, value => safeCommandName.test(value), 'command name must be safe');
    if (rawImport.write_policy !== undefined && (typeof rawImport.write_policy !== 'string' || rawImport.write_policy.trim() === '')) issues.push(issue(`${base}.write_policy`, 'write_policy must be a non-empty string'));
  }
}

function validateConnections(connections: unknown, issues: ValidationIssue[]): void {
  if (connections === undefined) return;
  if (!Array.isArray(connections)) {
    issues.push(issue('connections', 'connections must be an array when present'));
    return;
  }
  connections.forEach((rawConnection, index) => {
    const base = `connections.${index}`;
    if (!isObject(rawConnection)) {
      issues.push(issue(base, 'connection must be an object'));
      return;
    }
    if (typeof rawConnection.from !== 'string' || !safeName.test(rawConnection.from)) issues.push(issue(`${base}.from`, 'from must be a safe gadget name'));
    if (typeof rawConnection.to !== 'string' || !safeName.test(rawConnection.to)) issues.push(issue(`${base}.to`, 'to must be a safe gadget name'));
    if (rawConnection.via !== undefined && (typeof rawConnection.via !== 'string' || rawConnection.via.trim() === '')) issues.push(issue(`${base}.via`, 'via must be a non-empty string'));
    if (rawConnection.allowed_reads !== undefined) validateStringArray(`${base}.allowed_reads`, rawConnection.allowed_reads, issues, isSafeRelativePath, 'allowed read path must be safe and relative');
    if (rawConnection.allowed_commands !== undefined) validateStringArray(`${base}.allowed_commands`, rawConnection.allowed_commands, issues, value => safeCommandName.test(value), 'command name must be safe');
  });
}

export function readManifest(file: string): GizmoManifest {
  const text = fs.readFileSync(file, 'utf8');
  return JSON.parse(text) as GizmoManifest;
}

export function validateManifest(manifest: unknown): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (!isObject(manifest)) return [issue('$', 'manifest must be an object')];
  if (manifest.format !== GIZMO_FORMAT) issues.push(issue('format', `expected ${GIZMO_FORMAT}`));
  if (typeof manifest.name !== 'string' || manifest.name.trim() === '' || !safeName.test(manifest.name)) issues.push(issue('name', 'name must be a safe non-empty string'));
  if (!isObject(manifest.gadgets)) {
    issues.push(issue('gadgets', 'gadgets must be an object'));
    return issues;
  }
  for (const [name, rawGadget] of Object.entries(manifest.gadgets)) {
    const base = `gadgets.${name}`;
    if (!safeName.test(name)) issues.push(issue(base, 'gadget name must be filesystem-safe'));
    if (!isObject(rawGadget)) {
      issues.push(issue(base, 'gadget must be an object'));
      continue;
    }
    validateGadget(base, rawGadget, issues);
  }
  validateImports(manifest.imports, issues);
  validateConnections(manifest.connections, issues);
  return issues;
}

export function buildStatus(manifest: GizmoManifest): GizmoStatus {
  const gadgets = Object.entries(manifest.gadgets).map(([name, gadget]) => ({
    name,
    root: gadget.root,
    language: gadget.language ?? 'unknown',
    allowed_ops: gadget.allowed_ops ?? [],
    commands: Object.keys(gadget.commands).sort(),
    verification: gadget.promotion?.verification ?? (gadget.verification_profiles?.quick ? 'quick' : 'undeclared'),
    target_ref: gadget.target_ref,
    integration_branch: gadget.integration_branch,
    owned_paths: gadget.owned_paths ?? [],
  }));
  gadgets.sort((a, b) => a.name.localeCompare(b.name));
  const imports = Object.entries(manifest.imports ?? {}).map(([name, item]) => ({
    name,
    from_gizmo: item.from_gizmo,
    from_gadget: item.from_gadget,
    mode: item.mode,
    mount: item.mount,
    target_ref: item.target_ref,
    allowed_commands: [...(item.allowed_commands ?? [])].sort(),
    write_policy: item.write_policy,
  }));
  imports.sort((a, b) => a.name.localeCompare(b.name));
  return {
    format: GIZMO_FORMAT,
    name: manifest.name,
    gadget_count: gadgets.length,
    import_count: imports.length,
    connection_count: manifest.connections?.length ?? 0,
    gadgets,
    imports,
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
