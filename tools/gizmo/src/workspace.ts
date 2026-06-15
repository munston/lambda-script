import { buildProvisionPlan, ensureManifestValid } from './manifest';
import { GIZMO_WORKSPACE_PLAN_FORMAT, GizmoManifest, GizmoWorkspacePlan } from './types';

function normaliseRelativePath(value: string): string {
  const raw = value.replace(/\\/g, '/');
  const parts = raw.split('/');
  if (parts.length === 0) throw new Error('path must not be empty');
  for (const part of parts) {
    if (!part || part === '.' || part === '..') throw new Error(`unsafe workspace path: ${value}`);
  }
  return parts.join('/');
}

function normaliseWorkspaceRoot(value: string | undefined): string {
  if (value === undefined || value === '' || value === '.') return '.';
  if (value.includes('\0') || value.includes(':') || value.startsWith('/') || value.startsWith('\\')) throw new Error(`unsafe workspace root: ${value}`);
  return normaliseRelativePath(value);
}

function workspacePath(root: string, mount: string): string {
  const safeMount = normaliseRelativePath(mount);
  return root === '.' ? safeMount : `${root}/${safeMount}`;
}

function plannedAction(mode: 'read-only' | 'pinned' | 'copy'): 'bind-readonly' | 'checkout-pinned' | 'copy-on-write' {
  if (mode === 'copy') return 'copy-on-write';
  if (mode === 'pinned') return 'checkout-pinned';
  return 'bind-readonly';
}

export function buildWorkspacePlan(manifestInput: unknown, root?: string): GizmoWorkspacePlan {
  const manifest = ensureManifestValid(manifestInput) as GizmoManifest;
  const workspaceRoot = normaliseWorkspaceRoot(root);
  const provision = buildProvisionPlan(manifest);
  const mounts = provision.imports.map(item => ({
    name: item.name,
    source: item.source,
    mount: item.mount,
    workspace_path: workspacePath(workspaceRoot, item.mount),
    mode: item.mode,
    target_ref: item.target_ref,
    allowed_commands: item.allowed_commands,
    write_policy: item.write_policy,
    mutable: item.mutable,
    planned_action: plannedAction(item.mode),
  }));
  return {
    format: GIZMO_WORKSPACE_PLAN_FORMAT,
    name: manifest.name,
    workspace_root: workspaceRoot,
    mount_count: mounts.length,
    mounts,
  };
}
