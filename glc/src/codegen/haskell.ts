import { Program } from '../core/program';
import { Expression } from '../core/ast';

export function emitHaskell(program: Program): string {
  let output = '';
  for (const mod of program.modules) {
    output += `-- Module: ${mod.name}\n\n`;
    for (const decl of mod.declarations) {
      output += `${decl.name.name} = ${emitExpression(decl.value)}\n\n`;
    }
  }
  return output.trim();
}

function emitExpression(expr: Expression): string {
  if (expr.kind === 'Identifier') return expr.name;
  if (expr.kind === 'Literal') {
    if (typeof expr.value === 'string') return JSON.stringify(expr.value);
    if (typeof expr.value === 'boolean') return expr.value ? 'True' : 'False';
    return String(expr.value);
  }
  return '{- unsupported -}';
}
