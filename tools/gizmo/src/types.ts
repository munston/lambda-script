export const GIZMO_FORMAT = 'LS_GIZMO_V1';
export const GIZMO_PROVISION_PLAN_FORMAT = 'LS_GIZMO_PROVISION_PLAN_V1';

export type GadgetLanguage = 'python' | 'typescript' | 'lambdascript' | 'cpp' | 'mixed' | 'unknown';

export type GadgetOperation = 'read' | 'write' | 'mkdir' | 'copy' | 'run';

export type VerificationProfileName = 'quick' | 'full' | 'custom' | string;

export interface GadgetCommandMap {
  [name: string]: string;
}

export interface VerificationProfileMap {
  [name: string]: string[];
}

export interface GadgetManifest {
  root: string;
  language?: GadgetLanguage;
  allowed_ops?: GadgetOperation[];
  commands: GadgetCommandMap;
  description?: string;
  target_ref?: string;
  integration_branch?: string;
  agent_branch_template?: string;
  owned_paths?: string[];
  verification_profiles?: VerificationProfileMap;
  promotion?: {
    target?: string;
    verification?: VerificationProfileName;
  };
}

export interface GizmoImportManifest {
  from_gizmo: string;
  from_gadget: string;
  mount: string;
  mode: 'read-only' | 'pinned' | 'copy';
  target_ref?: string;
  allowed_commands?: string[];
  write_policy?: 'deny' | 'copy-on-write' | 'allow';
}

export interface GizmoConnectionManifest {
  from: string;
  to: string;
  via?: string;
  allowed_reads?: string[];
  allowed_commands?: string[];
}

export interface GizmoManifest {
  format: typeof GIZMO_FORMAT;
  name: string;
  description?: string;
  gadgets: Record<string, GadgetManifest>;
  imports?: Record<string, GizmoImportManifest>;
  connections?: GizmoConnectionManifest[];
}

export interface ValidationIssue {
  path: string;
  message: string;
}

export interface GizmoStatus {
  format: typeof GIZMO_FORMAT;
  name: string;
  description?: string;
  gadget_count: number;
  import_count: number;
  connection_count: number;
  gadgets: Array<{
    name: string;
    root: string;
    language: GadgetLanguage;
    allowed_ops: GadgetOperation[];
    commands: string[];
    owned_paths: string[];
    target_ref?: string;
    integration_branch?: string;
    agent_branch_template?: string;
    verification_profiles: string[];
    promotion_target?: string;
    promotion_verification: string;
  }>;
  imports: Array<{
    name: string;
    from_gizmo: string;
    from_gadget: string;
    mount: string;
    mode: string;
    target_ref?: string;
    allowed_commands: string[];
    write_policy?: string;
  }>;
  connections: GizmoConnectionManifest[];
}

export interface GizmoProvisionPlan {
  format: typeof GIZMO_PROVISION_PLAN_FORMAT;
  name: string;
  import_count: number;
  command_count: number;
  imports: Array<{
    name: string;
    source: string;
    mount: string;
    mode: 'read-only' | 'pinned' | 'copy';
    target_ref?: string;
    allowed_commands: string[];
    write_policy: 'deny' | 'copy-on-write' | 'allow';
    mutable: boolean;
  }>;
}
