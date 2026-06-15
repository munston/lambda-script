import { Program } from './program';
import { Diagnostic } from './diagnostic';
import { CallExpression, Expression, ForeignImport, ForeignPrimitiveType, FunctionDeclaration, FunctionSignature, UnaryExpression } from './ast';

type TypeName = ForeignPrimitiveType;

interface Scope {
  topLevel: Set<string>;
  locals: Map<string, TypeName>;
  signatures: Map<string, FunctionSignature>;
  values: Map<string, TypeName>;
}

export function checkProgram(program: Program): { diagnostics: Diagnostic[] } {
  const diagnostics: Diagnostic[] = [];
  const names = new Set<string>();
  const signatures = new Map<string, FunctionSignature>();
  const values = new Map<string, TypeName>();

  for (const mod of program.modules) {
    names.clear();
    signatures.clear();
    values.clear();

    for (const item of mod.declarations) {
      const name = item.name.name;
      if (names.has(name)) diagnostics.push({ message: `Duplicate top-level name: ${name}` });
      names.add(name);
      if (item.kind === 'FunctionDeclaration') signatures.set(name, (item as FunctionDeclaration).signature);
      if (item.kind === 'ForeignImport') signatures.set(name, (item as ForeignImport).signature);
    }

    for (const item of mod.declarations) {
      if (item.kind === 'ForeignImport') {
        const foreign = item as ForeignImport;
        if (foreign.signature.params.includes('void')) diagnostics.push({ message: `void cannot be a parameter type for ${foreign.name.name}` });
      }
    }

    for (const item of mod.declarations) {
      if (item.kind === 'FunctionDeclaration') {
        const fn = item as FunctionDeclaration;
        if (fn.signature.params.length !== fn.params.length) diagnostics.push({ message: `Wrong parameter count for ${fn.name.name}` });
        const localTypes = new Map<string, TypeName>();
        for (let i = 0; i < fn.params.length; i++) {
          const param = fn.params[i];
          if (localTypes.has(param.name)) diagnostics.push({ message: `Duplicate parameter ${param.name} in ${fn.name.name}` });
          localTypes.set(param.name, fn.signature.params[i]);
        }
        const bodyType = inferExpression(fn.body, { topLevel: names, locals: localTypes, signatures, values }, diagnostics);
        if (bodyType && !typeCompatible(bodyType, fn.signature.result)) diagnostics.push({ message: `Function ${fn.name.name} returns ${bodyType}, expected ${fn.signature.result}` });
      }
      if (item.kind === 'Declaration') {
        const t = inferExpression(item.value, { topLevel: names, locals: new Map<string, TypeName>(), signatures, values }, diagnostics);
        if (t) values.set(item.name.name, t);
      }
    }
  }
  return { diagnostics };
}

function inferExpression(expr: Expression, scope: Scope, diagnostics: Diagnostic[]): TypeName | undefined {
  if (expr.kind === 'Literal') {
    if (typeof expr.value === 'boolean') return 'bool';
    if (typeof expr.value === 'string') return 'string';
    if (typeof expr.value === 'number') return Number.isInteger(expr.value) ? 'i32' : 'f64';
  }
  if (expr.kind === 'Identifier') {
    if (scope.locals.has(expr.name)) return scope.locals.get(expr.name);
    if (scope.values.has(expr.name)) return scope.values.get(expr.name);
    if (scope.signatures.has(expr.name)) diagnostics.push({ message: `Function used as value: ${expr.name}` });
    else if (!scope.topLevel.has(expr.name)) diagnostics.push({ message: `Unknown identifier: ${expr.name}` });
    else diagnostics.push({ message: `Unknown value type: ${expr.name}` });
    return undefined;
  }
  if (expr.kind === 'CallExpression') {
    const call = expr as CallExpression;
    const callee = call.callee.name;
    const signature = scope.signatures.get(callee);
    if (!scope.topLevel.has(callee)) {
      diagnostics.push({ message: `Unknown function: ${callee}` });
    } else if (!signature) {
      diagnostics.push({ message: `Cannot call non-function value: ${callee}` });
    } else {
      if (call.arguments.length !== signature.params.length) diagnostics.push({ message: `Wrong argument count for ${callee}` });
      for (let i = 0; i < call.arguments.length; i++) {
        const actual = inferExpression(call.arguments[i], scope, diagnostics);
        const expected = signature.params[i];
        if (actual && expected && !typeCompatible(actual, expected)) diagnostics.push({ message: `Argument ${i + 1} for ${callee} has type ${actual}, expected ${expected}` });
      }
      return signature.result;
    }
    for (const arg of call.arguments) inferExpression(arg, scope, diagnostics);
    return undefined;
  }
  if (expr.kind === 'UnaryExpression') {
    const unary = expr as UnaryExpression;
    const operand = inferExpression(unary.operand, scope, diagnostics);
    if (operand && operand !== 'bool') diagnostics.push({ message: `Unary ${unary.operator} expects bool operand, got ${operand}` });
    return 'bool';
  }
  if (expr.kind === 'BinaryExpression') {
    const left = inferExpression(expr.left, scope, diagnostics);
    const right = inferExpression(expr.right, scope, diagnostics);
    return inferBinaryType(expr.operator, left, right, diagnostics);
  }
  if (expr.kind === 'IfExpression') {
    const condition = inferExpression(expr.condition, scope, diagnostics);
    const thenType = inferExpression(expr.thenBranch, scope, diagnostics);
    const elseType = inferExpression(expr.elseBranch, scope, diagnostics);
    if (condition && condition !== 'bool') diagnostics.push({ message: `If condition has type ${condition}, expected bool` });
    if (thenType && elseType && !typeCompatible(thenType, elseType) && !typeCompatible(elseType, thenType)) diagnostics.push({ message: `If branches have different types: ${thenType} and ${elseType}` });
    if (thenType && elseType) return thenType === 'f64' || elseType === 'f64' ? 'f64' : thenType;
    return undefined;
  }
  if (expr.kind === 'LetExpression') {
    const valueType = inferExpression(expr.value, scope, diagnostics);
    const innerLocals = new Map(scope.locals);
    if (valueType) innerLocals.set(expr.name.name, valueType);
    return inferExpression(expr.body, { topLevel: scope.topLevel, locals: innerLocals, signatures: scope.signatures, values: scope.values }, diagnostics);
  }
  return undefined;
}

function inferBinaryType(op: string, left: TypeName | undefined, right: TypeName | undefined, diagnostics: Diagnostic[]): TypeName | undefined {
  if (!left || !right) return undefined;
  if (['+', '-', '*', '/'].includes(op)) {
    if (!isNumeric(left) || !isNumeric(right)) {
      diagnostics.push({ message: `Operator ${op} expects numeric operands, got ${left} and ${right}` });
      return undefined;
    }
    return left === 'f64' || right === 'f64' ? 'f64' : 'i32';
  }
  if (['&&', '||'].includes(op)) {
    if (left !== 'bool' || right !== 'bool') diagnostics.push({ message: `Operator ${op} expects bool operands, got ${left} and ${right}` });
    return 'bool';
  }
  if (['<', '>', '<=', '>='].includes(op)) {
    if (!isNumeric(left) || !isNumeric(right)) diagnostics.push({ message: `Operator ${op} expects numeric operands, got ${left} and ${right}` });
    return 'bool';
  }
  if (['==', '!='].includes(op)) {
    if (!typeCompatible(left, right) && !typeCompatible(right, left)) diagnostics.push({ message: `Operator ${op} expects matching operands, got ${left} and ${right}` });
    return 'bool';
  }
  diagnostics.push({ message: `Unknown binary operator: ${op}` });
  return undefined;
}

function typeCompatible(actual: TypeName, expected: TypeName): boolean {
  return actual === expected || (actual === 'i32' && expected === 'f64');
}

function isNumeric(t: TypeName): boolean {
  return t === 'i32' || t === 'f64';
}
