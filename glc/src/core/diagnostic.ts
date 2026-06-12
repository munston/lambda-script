import { Span } from './ast';
import { Program } from './program';

export interface Diagnostic {
  message: string;
  span?: Span;
}

export interface CheckResult {
  program: Program;
  diagnostics: Diagnostic[];
}
