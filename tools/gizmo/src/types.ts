export const GIZMO_FORMAT = 'LS_GIZMO_V1';

export type GadgetLanguage = 'python' | 'typescript' | 'lambdascript' | 'cpp' | 'mixed' | 'unknown';

export type GadgetOperation = 'read' | 'write' | 'mkdir' | 'copy' | 'run';

export interface GadgetCommandMap {
  [name: string]: string;
}

export interface VerificationProfiles {
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
  verification_profiles?: VerificationProfiles;
  promotion?: {
    target?: string;
    verification?: 'quick' | 'full' | 'custom' | string;
  };
}

export interface GizmoImportManifest {
  from_gizmo: string;
  from_gadget: string;
  mount: string;
  mode: 'read-only' | 'read-write' | string;
  target_ref?: string;
  allowed_commands?: string[];
  write_policy?: 'deny' | 'allow-owned' | string;
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
  gadget_count: number;
  import_count: number;
  connection_count: number;
  gadgets: Array<{
    name: string;
    root: string;
    language: GadgetLanguage;
    allowed_ops: GadgetOperation[];
    commands: string[];
    verification: string;
    target_ref?: string;
    integration_branch?: string;
    owned_paths: string[];
  }>;
  imports: Array<{
    name: string;
    from_gizmo: string;
    from_gadget: string;
    mode: string;
    mount: string;
    target_ref?: string;
    allowed_commands: string[];
    write_policy?: string;
  }>;
}
