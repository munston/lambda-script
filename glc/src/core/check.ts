import { Program } from './program';
import { CheckResult } from './diagnostic';

/**
 * No-op checker.
 * Returns the program with an empty diagnostics list.
 * This is the attachment point for future semantic analysis.
 */
export function checkProgram(program: Program): CheckResult {
  return {
    program,
    diagnostics: [],
  };
}
