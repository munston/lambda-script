import { Program, Module } from '../core/program';
import { Declaration, Expression, Span, ForeignImport, ForeignSignature, FunctionSignature, ForeignPrimitiveType } from '../core/ast';
import { Diagnostic } from '../core/diagnostic';

export interface ParseResult {
  program?: Program;
  diagnostics: Diagnostic[];
}

const VALID_FFI = ['i32', 'f64', 'bool', 'string', 'void', 'handle', 'f64buf', 'i32buf'];
const BINARY_PRECEDENCE: string[][] = [
  ['||'],
  ['&&'],
  ['==', '!=', '<=', '>=', '<', '>'],
  ['+', '-'],
  ['*', '/'],
];

function isValidFFIType(t: string): boolean {
  return VALID_FFI.includes(t);
}

function parseSignature(text: string): FunctionSignature | undefined {
  const parts = text.split('->').map(s => s.trim());
  if (parts.length < 2) return undefined;
  const resultType = parts[parts.length - 1];
  const paramTypes = parts.slice(0, -1);
  if (!isValidFFIType(resultType) || paramTypes.some(t => !isValidFFIType(t))) return undefined;
  if (paramTypes.includes('void')) return undefined;
  return { params: paramTypes as ForeignPrimitiveType[], result: resultType as ForeignPrimitiveType };
}

function stripOuterParens(text: string): string {
  let s = text.trim();
  while (s.startsWith('(') && s.endsWith(')')) {
    let depth = 0;
    let wraps = true;
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (ch === '(') depth++;
      if (ch === ')') depth--;
      if (depth === 0 && i < s.length - 1) {
        wraps = false;
        break;
      }
    }
    if (!wraps) break;
    s = s.slice(1, -1).trim();
  }
  return s;
}

function findKeywordAtTopLevel(text: string, keyword: string): number {
  let depth = 0;
  let inString = false;
  for (let i = 0; i <= text.length - keyword.length; i++) {
    const ch = text[i];
    if (ch === '"') inString = !inString;
    if (inString) continue;
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (depth !== 0) continue;
    if (text.slice(i, i + keyword.length) === keyword) {
      const before = i === 0 ? ' ' : text[i - 1];
      const after = i + keyword.length >= text.length ? ' ' : text[i + keyword.length];
      if (/\s/.test(before) && /\s/.test(after)) return i;
    }
  }
  return -1;
}

function findBindingEqualsAtTopLevel(text: string): number {
  let depth = 0;
  let inString = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') inString = !inString;
    if (inString) continue;
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (depth !== 0 || ch !== '=') continue;
    const prev = i > 0 ? text[i - 1] : '';
    const next = i + 1 < text.length ? text[i + 1] : '';
    if (prev === '<' || prev === '>' || prev === '!' || prev === '=' || next === '=') continue;
    return i;
  }
  return -1;
}

function findOperatorAtTopLevel(text: string, ops: string[]): { index: number; op: string } | undefined {
  let depth = 0;
  let inString = false;
  for (let i = text.length - 1; i >= 0; i--) {
    const ch = text[i];
    if (ch === '"') inString = !inString;
    if (inString) continue;
    if (ch === ')') depth++;
    if (ch === '(') depth--;
    if (depth !== 0) continue;
    for (const op of ops) {
      const start = i - op.length + 1;
      if (start < 0) continue;
      if (text.slice(start, i + 1) !== op) continue;
      const prev = start > 0 ? text[start - 1] : '';
      if ((op === '-' || op === '+') && (start === 0 || ['+', '-', '*', '/', '<', '>', '=', '!', '('].includes(prev))) continue;
      return { index: start, op };
    }
  }
  return undefined;
}

function splitArgs(text: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let inString = false;
  let start = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') inString = !inString;
    if (inString) continue;
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (ch === ',' && depth === 0) {
      out.push(text.slice(start, i).trim());
      start = i + 1;
    }
  }
  const last = text.slice(start).trim();
  if (last.length > 0) out.push(last);
  return out;
}

function parseExpression(text: string, span: Span): Expression | undefined {
  const s = stripOuterParens(text);
  if (s.startsWith('let ')) {
    const inIdx = findKeywordAtTopLevel(s, 'in');
    if (inIdx > 0) {
      const binding = s.slice(4, inIdx).trim();
      const eqIdx = findBindingEqualsAtTopLevel(binding);
      if (eqIdx > 0) {
        const nameText = binding.slice(0, eqIdx).trim();
        const valueText = binding.slice(eqIdx + 1).trim();
        const bodyText = s.slice(inIdx + 2).trim();
        if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(nameText)) {
          const value = parseExpression(valueText, span);
          const body = parseExpression(bodyText, span);
          if (value && body) return { kind: 'LetExpression', name: { kind: 'Identifier', name: nameText, span }, value, body, span };
        }
      }
    }
  }
  if (s.startsWith('if ')) {
    const thenIdx = findKeywordAtTopLevel(s, 'then');
    if (thenIdx > 0) {
      const elseIdx = findKeywordAtTopLevel(s.slice(thenIdx + 4), 'else');
      if (elseIdx >= 0) {
        const condText = s.slice(3, thenIdx).trim();
        const thenText = s.slice(thenIdx + 4, thenIdx + 4 + elseIdx).trim();
        const elseText = s.slice(thenIdx + 4 + elseIdx + 4).trim();
        const condition = parseExpression(condText, span);
        const thenBranch = parseExpression(thenText, span);
        const elseBranch = parseExpression(elseText, span);
        if (condition && thenBranch && elseBranch) return { kind: 'IfExpression', condition, thenBranch, elseBranch, span };
      }
    }
  }
  for (const ops of BINARY_PRECEDENCE) {
    const found = findOperatorAtTopLevel(s, ops);
    if (found) {
      const left = parseExpression(s.slice(0, found.index).trim(), span);
      const right = parseExpression(s.slice(found.index + found.op.length).trim(), span);
      if (left && right) return { kind: 'BinaryExpression', operator: found.op, left, right, span };
    }
  }
  if (s.startsWith('not ')) {
    const operand = parseExpression(s.slice(4).trim(), span);
    if (operand) return { kind: 'UnaryExpression', operator: 'not', operand, span };
    return undefined;
  }
  if (s === 'true' || s === 'false') return { kind: 'Literal', value: s === 'true', span };
  if (!isNaN(Number(s))) return { kind: 'Literal', value: Number(s), span };
  if (s.startsWith('"') && s.endsWith('"')) return { kind: 'Literal', value: s.slice(1, -1), span };
  const callMatch = s.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)$/);
  if (callMatch) {
    const callee = { kind: 'Identifier' as const, name: callMatch[1], span };
    const args = callMatch[2].trim().length === 0 ? [] : splitArgs(callMatch[2]).map(a => parseExpression(a, span));
    if (args.every(Boolean)) return { kind: 'CallExpression', callee, arguments: args as Expression[], span };
    return undefined;
  }
  if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(s)) return { kind: 'Identifier', name: s, span };
  return undefined;
}

function flushPendingSignatures(moduleName: string, pending: Map<string, FunctionSignature>, diagnostics: Diagnostic[]): void {
  for (const name of pending.keys()) diagnostics.push({ message: `Dangling type signature for ${name} in module ${moduleName}` });
  pending.clear();
}

export function parse(source: string, filename = 'input.ls'): ParseResult {
  const lines = source.split(/\r?\n/);
  let currentModule: Module | null = null;
  const modules: Module[] = [];
  const diagnostics: Diagnostic[] = [];
  const pendingSignatures = new Map<string, FunctionSignature>();

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();
    if (!line || line.startsWith('//')) continue;

    const moduleMatch = line.match(/^module\s+([A-Za-z_][A-Za-z0-9_]*)$/);
    if (moduleMatch) {
      if (currentModule) {
        flushPendingSignatures(currentModule.name, pendingSignatures, diagnostics);
        modules.push(currentModule);
      }
      currentModule = { kind: 'Module', name: moduleMatch[1], declarations: [] };
      pendingSignatures.clear();
      continue;
    }

    const typeSigMatch = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$/);
    if (typeSigMatch && currentModule) {
      const signature = parseSignature(typeSigMatch[2].trim());
      if (!signature) {
        diagnostics.push({ message: `Invalid type signature at line ${i+1}` });
        continue;
      }
      if (pendingSignatures.has(typeSigMatch[1])) {
        diagnostics.push({ message: `Duplicate type signature for ${typeSigMatch[1]} at line ${i+1}` });
        continue;
      }
      pendingSignatures.set(typeSigMatch[1], signature);
      continue;
    }

    const foreignMatch = line.match(/^foreign\s+cpp\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\s*=\s*"([^"]+)"$/);
    if (foreignMatch && currentModule) {
      const localName = foreignMatch[1];
      const signature = parseSignature(foreignMatch[2].trim());
      const symbol = foreignMatch[3];
      if (!signature) {
        diagnostics.push({ message: `Invalid foreign signature at line ${i+1}` });
        continue;
      }
      const imp: ForeignImport = {
        kind: 'ForeignImport',
        target: 'cpp',
        name: { kind: 'Identifier', name: localName },
        symbol,
        signature: signature as ForeignSignature
      };
      currentModule.declarations.push(imp);
      continue;
    }

    const functionMatch = line.match(/^([A-Za-z_][A-Za-z0-9_]*)(\s+[A-Za-z_][A-Za-z0-9_]*)+\s*=\s*(.+)$/);
    if (functionMatch && currentModule) {
      const eqIdx = line.indexOf('=');
      const left = line.slice(0, eqIdx).trim().split(/\s+/);
      const name = left[0];
      const params = left.slice(1).map(p => ({ kind: 'Identifier' as const, name: p }));
      const signature = pendingSignatures.get(name);
      if (!signature) {
        diagnostics.push({ message: `Missing type signature for function ${name} at line ${i+1}` });
        continue;
      }
      if (signature.params.length !== params.length) {
        diagnostics.push({ message: `Parameter count does not match signature for ${name} at line ${i+1}` });
        pendingSignatures.delete(name);
        continue;
      }
      const span: Span = { file: filename, start: i, end: i };
      const body = parseExpression(line.slice(eqIdx + 1).trim(), span);
      if (!body) {
        diagnostics.push({ message: `Invalid function body at line ${i+1}` });
        pendingSignatures.delete(name);
        continue;
      }
      currentModule.declarations.push({
        kind: 'FunctionDeclaration',
        name: { kind: 'Identifier', name },
        params,
        signature,
        body,
        span
      });
      pendingSignatures.delete(name);
      continue;
    }

    const declMatch = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$/);
    if (declMatch && currentModule) {
      const name = declMatch[1];
      const valueStr = declMatch[2].trim();
      const span: Span = { file: filename, start: i, end: i };
      const value = parseExpression(valueStr, span);
      if (!value) {
        diagnostics.push({ message: `Invalid expression at line ${i+1}` });
        continue;
      }
      const decl: Declaration = {
        kind: 'Declaration',
        name: { kind: 'Identifier', name },
        value
      };
      currentModule.declarations.push(decl);
      continue;
    }

    diagnostics.push({ message: `Invalid line at ${i+1}: ${rawLine.trim()}` });
  }

  if (currentModule) {
    flushPendingSignatures(currentModule.name, pendingSignatures, diagnostics);
    modules.push(currentModule);
  }

  return {
    program: diagnostics.length === 0 ? { kind: 'Program', modules } : undefined,
    diagnostics
  };
}
