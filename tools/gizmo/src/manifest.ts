declare const require: any;
const fs = require('fs');
const path = require('path');

import {
  GIZMO_FORMAT,
  GIZMO_PROVISION_PLAN_FORMAT,
  GadgetLanguage,
  GadgetOperation,
  GizmoConnectionManifest,
  GizmoImportManifest,
  GizmoManifest,
  GizmoProvisionPlan,
  GizmoStatus,
  ValidationIssue,
} from './types';

const allowedLanguages = new Set<GadgetLanguage>(['python', 'typescript', 'lambdascript', 'cpp', 'mixed', 'unknown']);
const allowedOps = new Set<GadgetOperation>(['read', 'write', 'mkdir', 'copy', 'run']);
const allowedImportModes = new Set(['read-only', 'pinned', 'copy']);
const allowedWritePolicies = new Set(['deny', 'copy-on-write', 'allow']);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSafeName(value: string): boolean {
  return /^[A-Za-z0-9._-]+$/.test(value);
}

function isSafeRef(value: string): boolean {
  return /^[A-Za-z0-9._/-]+$/.test(value) && !value.includes('..') && !value.startsWith('/') && !value.endsWith('/');
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

function stringArrayIssues(value: unknown, pathName: string, itemLabel: string): ValidationIssue[] {
  if (!Array.isArray(value)) return [issue(pathName, `${itemLabel} must be an array`)];
  return value.flatMap((item, i) => typeof item === 'string' && item.trim() !== '' ? [] : [issue(`${pathName}.${i}`, `${itemLabel} entry must be a non-empty string`)]);
}

function optionalStringArrayIssues(value: unknown, pathName: string, itemLabel: string): ValidationIssue[] {
  if (value === undefined) return [];
  return stringArrayIssues(value, pathName, itemLabel);
}

export function readManifest(file: string): GizmoManifest {
  const text = fs.readFileSync(file, 'utf8');
  return JSON.parse(text) as GizmoManifest;
}

function validateGadget(name: string, rawGadget: unknown): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const base = `gadgets.${name}`;
  if (!isSafeName(name)) issues.push(issue(base, 'gadget name must be filesystem-safe'));
  if (!isObject(rawGadget)) return [...issues, issue(base, 'gadget must be an object')];

  if (typeof rawGadget.root !== 'string' || !isSafeRelativePath(rawGadget.root)) issues.push(issue(`${base}.root`, 'root must be a safe relative path'));

  const language = rawGadget.language ?? 'unknown';
  if (typeof language !== 'string' || !allowedLanguages.has(language as GadgetLanguage)) issues.push(issue(`${base}.language`, 'unsupported language'));

  const allowedOpsValue = rawGadget.allowed_ops ?? [];
  if (!Array.isArray(allowedOpsValue)) {
    issues.push(issue(`${base}.allowed_ops`, 'allowed_ops must be an array when present'));
  } else {
    for (const op of allowedOpsValue) {
      if (typeof op !== 'string' || !allowedOps.has(op as GadgetOperation)) issues.push(issue(`${base}.allowed_ops`, `unsupported operation ${String(op)}`));
    }
  }

  if (!isObject(rawGadget.commands)) {
    issues.push(issue(`${base}.commands`, 'commands must be an object'));
  } else {
    for (const [commandName, command] of Object.entries(rawGadget.commands)) {
      if (!isSafeName(commandName)) issues.push(issue(`${base}.commands.${commandName}`, 'command name must be safe'));
      if (typeof command !== 'string' || command.trim() === '') issues.push(issue(`${base}.commands.${commandName}`, 'command must be a non-empty string'));
    }
  }

  if (rawGadget.target_ref !== undefined && (typeof rawGadget.target_ref !== 'string' || !isSafeRef(rawGadget.target_ref))) issues.push(issue(`${base}.target_ref`, 'target_ref must be a safe git ref'));
  if (rawGadget.integration_branch !== undefined && (typeof rawGadget.integration_branch !== 'string' || !isSafeRef(rawGadget.integration_branch))) issues.push(issue(`${base}.integration_branch`, 'integration_branch must be a safe git ref'));
  if (rawGadget.agent_branch_template !== undefined && (typeof rawGadget.agent_branch_template !== 'string' || !rawGadget.agent_branch_template.includes('{agent}') || !isSafeRef(rawGadget.agent_branch_template.replace('{agent}', 'agent')))) {
    issues.push(issue(`${base}.agent_branch_template`, 'agent_branch_template must be a safe ref template containing {agent}'));
  }

  issues.push(...optionalStringArrayIssues(rawGadget.owned_paths, `${base}.owned_paths`, 'owned_paths'));
  if (Array.isArray(rawGadget.owned_paths)) {
    for (const [i, item] of rawGadget.owned_paths.entries()) {
      if (typeof item === 'string' && !isSafeRelativePath(item.replace(/\/$/, ''))) issues.push(issue(`${base}.owned_paths.${i}`, 'owned path must be safe and relative'));
    }
  }

  if (rawGadget.verification_profiles !== undefined) {
    if (!isObject(rawGadget.verification_profiles)) {
      issues.push(issue(`${base}.verification_profiles`, 'verification_profiles must be an object'));
    } else {
      for (const [profileName, commands] of Object.entries(rawGadget.verification_profiles)) {
        if (!isSafeName(profileName)) issues.push(issue(`${base}.verification_profiles.${profileName}`, 'profile name must be safe'));
        issues.push(...stringArrayIssues(commands, `${base}.verification_profiles.${profileName}`, 'verification command'));
      }
    }
  }

  if (rawGadget.promotion !== undefined) {
    if (!isObject(rawGadget.promotion)) {
      issues.push(issue(`${base}.promotion`, 'promotion must be an object'));
    } else {
      if (rawGadget.promotion.target !== undefined && typeof rawGadget.promotion.target !== 'string') issues.push(issue(`${base}.promotion.target`, 'target must be a string'));
      if (rawGadget.promotion.verification !== undefined && typeof rawGadget.promotion.verification !== 'string') issues.push(issue(`${base}.promotion.verification`, 'verification must be a string'));
    }
  }

  return issues;
}

function validateImport(name: string, rawImport: unknown): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const base = `imports.${name}`;
  if (!isSafeName(name)) issues.push(issue(base, 'import name must be safe'));
  if (!isObject(rawImport)) return [...issues, issue(base, 'import must be an object')];

  for (const key of ['from_gizmo', 'from_gadget', 'mount', 'mode']) {
    if (typeof rawImport[key] !== 'string' || String(rawImport[key]).trim() === '') issues.push(issue(`${base}.${key}`, `${key} must be a non-empty string`));
  }

  if (typeof rawImport.from_gizmo === 'string' && !isSafeName(rawImport.from_gizmo)) issues.push(issue(`${base}.from_gizmo`, 'from_gizmo must be safe'));
  if (typeof rawImport.from_gadget === 'string' && !isSafeName(rawImport.from_gadget)) issues.push(issue(`${base}.from_gadget`, 'from_gadget must be safe'));
  if (typeof rawImport.mount === 'string' && !isSafeRelativePath(rawImport.mount)) issues.push(issue(`${base}.mount`, 'mount must be a safe relative path'));
  if (typeof rawImport.mode !== 'string' || !allowedImportModes.has(rawImport.mode)) issues.push(issue(`${base}.mode`, 'unsupported import mode'));
  if (rawImport.target_ref !== undefined && (typeof rawImport.target_ref !== 'string' || !isSafeRef(rawImport.target_ref))) issues.push(issue(`${base}.target_ref`, 'target_ref must be a safe git ref'));
  issues.push(...optionalStringArrayIssues(rawImport.allowed_commands, `${base}.allowed_commands`, 'allowed command'));
  if (rawImport.write_policy !== undefined && (typeof rawImport.write_policy !== 'string' || !allowedWritePolicies.has(rawImport.write_policy))) issues.push(issue(`${base}.write_policy`, 'unsupported write policy'));

  return issues;
}

function validateConnection(index: number, rawConnection: unknown, gadgetNames: Set<string>): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const base = `connections.${index}`;
  if (!isObject(rawConnection)) return [issue(base, 'connection must be an object')];

  for (const key of ['from', 'to']) {
    const value = rawConnection[key];
    if (typeof value !== 'string' || !gadgetNames.has(value)) issues.push(issue(`${base}.${key}`, `${key} must name a local gadget`));
  }

  if (rawConnection.via !== undefined && typeof rawConnection.via !== 'string') issues.push(issue(`${base}.via`, 'via must be a string'));
  issues.push(...optionalStringArrayIssues(rawConnection.allowed_reads, `${base}.allowed_reads`, 'allowed read'));
  issues.push(...optionalStringArrayIssues(rawConnection.allowed_commands, `${base}.allowed_commands`, 'allowed command'));
  return issues;
}

export function validateManifest(manifest: unknown): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (!isObject(manifest)) return [issue('$', 'manifest must be an object')];
  if (manifest.format !== GIZMO_FORMAT) issues.push(issue('format', `expected ${GIZMO_FORMAT}`));
  if (typeof manifest.name !== 'string' || manifest.name.trim() === '' || !isSafeName(manifest.name)) issues.push(issue('name', 'name must be a non-empty safe string'));

  if (!isObject(manifest.gadgets)) {
    issues.push(issue('gadgets', 'gadgets must be an object'));
    return issues;
  }

  const gadgetNames = new Set(Object.keys(manifest.gadgets));
  for (const [name, rawGadget] of Object.entries(manifest.gadgets)) {
    issues.push(...validateGadget(name, rawGadget));
  }

  if (manifest.imports !== undefined) {
    if (!isObject(manifest.imports)) {
      issues.push(issue('imports', 'imports must be an object'));
    } else {
      for (const [name, rawImport] of Object.entries(manifest.imports)) {
        issues.push(...validateImport(name, rawImport));
      }
    }
  }

  if (manifest.connections !== undefined) {
    if (!Array.isArray(manifest.connections)) {
      issues.push(issue('connections', 'connections must be an array'));
    } else {
      manifest.connections.forEach((item, i) => issues.push(...validateConnection(i, item, gadgetNames)));
    }
  }

  return issues;
}

export function buildStatus(manifest: GizmoManifest): GizmoStatus {
  const gadgets = Object.entries(manifest.gadgets).map(([name, gadget]) => ({
    name,
    root: gadget.root,
    language: gadget.language ?? 'unknown',
    allowed_ops: gadget.allowed_ops ?? [],
    commands: Object.keys(gadget.commands).sort(),
    owned_paths: [...(gadget.owned_paths ?? [])].sort(),
    target_ref: gadget.target_ref,
    integration_branch: gadget.integration_branch,
    agent_branch_template: gadget.agent_branch_template,
    verification_profiles: Object.keys(gadget.verification_profiles ?? {}).sort(),
    promotion_target: gadget.promotion?.target,
    promotion_verification: gadget.promotion?.verification ?? 'quick',
  }));
  gadgets.sort((a, b) => a.name.localeCompare(b.name));

  const imports = Object.entries(manifest.imports ?? {}).map(([name, item]) => ({
    name,
    from_gizmo: item.from_gizmo,
    from_gadget: item.from_gadget,
    mount: item.mount,
    mode: item.mode,
    target_ref: item.target_ref,
    allowed_commands: [...(item.allowed_commands ?? [])].sort(),
    write_policy: item.write_policy,
  }));
  imports.sort((a, b) => a.name.localeCompare(b.name));

  return {
    format: GIZMO_FORMAT,
    name: manifest.name,
    description: manifest.description,
    gadget_count: gadgets.length,
    import_count: imports.length,
    connection_count: manifest.connections?.length ?? 0,
    gadgets,
    imports,
    connections: [...(manifest.connections ?? [])],
  };
}

export function buildProvisionPlan(manifest: GizmoManifest): GizmoProvisionPlan {
  const imports = Object.entries(manifest.imports ?? {}).map(([name, item]) => {
    const writePolicy = item.write_policy ?? (item.mode === 'copy' ? 'copy-on-write' : 'deny');
    const mutable = writePolicy === 'allow' || writePolicy === 'copy-on-write';
    return {
      name,
      source: `${item.from_gizmo}/${item.from_gadget}`,
      mount: item.mount,
      mode: item.mode,
      target_ref: item.target_ref,
      allowed_commands: [...(item.allowed_commands ?? [])].sort(),
      write_policy: writePolicy,
      mutable,
    };
  });
  imports.sort((a, b) => a.name.localeCompare(b.name));
  return {
    format: GIZMO_PROVISION_PLAN_FORMAT,
    name: manifest.name,
    import_count: imports.length,
    command_count: imports.reduce((total, item) => total + item.allowed_commands.length, 0),
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
