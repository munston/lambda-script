import { Program } from './program';
import { Diagnostic } from './diagnostic';
import { CallExpression, Expression, ForeignImport, FunctionDeclaration } from './ast';

interface Scope {
  topLevel: Set<string>;
  locals: Set<string>;
}

export function checkProgram(program: Program): { diagnostics: Diagnostic[] } {
  const diagnostics: Diagnostic[] = [];
  const names = new Set<string>();

  for (const mod of program.modules) {
    names.clear();
    for (const item of mod.declarations) {
      const name = item.name.name;
      if (names.has(name)) diagnostics.push({ message: `Duplicate top-level name: ${name}` });
      names.add(name);
    }

    for (const item of mod.declarations) {
      if (item.kind === 'FunctionDeclaration') {
        const fn = item as FunctionDeclaration;
        if (fn.signature.params.length !== fn.params.length) diagnostics.push({ message: `Wrong parameter count for ${fn.name.name}` });
        const localNames = new Set<string>();
        for (const param of fn.params) {
          if (localNames.has(param.name)) diagnostics.push({ message: `Duplicate parameter ${param.name} in ${fn.name.name}` });
          localNames.add(param.name);
        }
        checkExpression(fn.body, { topLevel: names, locals: localNames }, diagnostics);
      }
      if (item.kind === 'Declaration') {
        checkExpression(item.value, { topLevel: names, locals: new Set<string>() }, diagnostics);
      }
      if (item.kind === 'ForeignImport') {
        const foreign = item as ForeignImport;
        if (foreign.signature.params.includes('void')) diagnostics.push({ message: `void cannot be a parameter type for ${foreign.name.name}` });
      }
    }
  }
  return { diagnostics };
}

function checkExpression(expr: Expression, scope: Scope, diagnostics: Diagnostic[]): void {
  if (expr.kind === 'Literal') return;
  if (expr.kind === 'Identifier') {
    if (!scope.locals.has(expr.name) && !scope.topLevel.has(expr.name)) diagnostics.push({ message: `Unknown identifier: ${expr.name}` });
    return;
  }
  if (expr.kind === 'CallExpression') {
    const call = expr as CallExpression;
    const callee = call.callee.name;
    if (!scope.topLevel.has(callee)) diagnostics.push({ message: `Unknown function: ${callee}` });
    for (const arg of call.arguments) checkExpression(arg, scope, diagnostics);
    return;
  }
  if (expr.kind === 'BinaryExpression') {
    checkExpression(expr.left, scope, diagnostics);
    checkExpression(expr.right, scope, diagnostics);
    return;
  }
  if (expr.kind === 'IfExpression') {
    checkExpression(expr.condition, scope, diagnostics);
    checkExpression(expr.thenBranch, scope, diagnostics);
    checkExpression(expr.elseBranch, scope, diagnostics);
  }
}
