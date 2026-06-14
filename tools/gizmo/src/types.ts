export const GIZMO_FORMAT = 'LS_GIZMO_V1';

export type GadgetLanguage = 'python' | 'typescript' | 'lambdascript' | 'cpp' | 'mixed' | 'unknown';

export type GadgetOperation = 'read' | 'write' | 'mkdir' | 'copy' | 'run';

export interface GadgetCommandMap {
  [name: string]: string;
}

export interface GadgetManifest {
  root: string;
  language?: GadgetLanguage;
  allowed_ops: GadgetOperation[];
  commands: GadgetCommandMap;
  description?: string;
  promotion?: {
    target?: string;
    verification?: 'quick' | 'full' | 'custom';
  };
}

export interface GizmoManifest {
  format: typeof GIZMO_FORMAT;
  name: string;
  description?: string;
  gadgets: Record<string, GadgetManifest>;
}

export interface ValidationIssue {
  path: string;
  message: string;
}

export interface GizmoStatus {
  format: typeof GIZMO_FORMAT;
  name: string;
  gadget_count: number;
  gadgets: Array<{
    name: string;
    root: string;
    language: GadgetLanguage;
    allowed_ops: GadgetOperation[];
    commands: string[];
    verification: string;
  }>;
}
