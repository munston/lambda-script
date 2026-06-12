import { Program, Module } from '../core/program';
import { Declaration, Expression, Span, ForeignImport, ForeignSignature } from '../core/ast';
import { Diagnostic } from '../core/diagnostic';

export interface ParseResult {
  program?: Program;
  diagnostics: Diagnostic[];
}

const VALID_FFI = ['i32', 'f64', 'bool', 'string', 'void'];

function isValidFFIType(t: string): boolean {
  return VALID_FFI.includes(t);
}

export function parse(source: string, filename = 'input.ls'): ParseResult {
  const lines = source.split(/\r?\n/);
  let currentModule: Module | null = null;
  const modules: Module[] = [];
  const diagnostics: Diagnostic[] = [];

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();
    if (!line || line.startsWith('//')) continue;

    const moduleMatch = line.match(/^module\s+([A-Za-z_][A-Za-z0-9_]*)$/);
    if (moduleMatch) {
      if (currentModule) modules.push(currentModule);
      currentModule = { kind: 'Module', name: moduleMatch[1], declarations: [] };
      continue;
    }

    const foreignMatch = line.match(/^foreign\s+cpp\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\s*=\s*"([^"]+)"$/);
    if (foreignMatch && currentModule) {
      const localName = foreignMatch[1];
      const sigStr = foreignMatch[2].trim();
      const symbol = foreignMatch[3];
      const parts = sigStr.split('->').map(s => s.trim());

      if (parts.length < 2) {
        diagnostics.push({ message: `Invalid foreign signature at line ${i+1}` });
        continue;
      }

      const resultType = parts[parts.length - 1];
      const paramTypes = parts.slice(0, -1);

      if (!isValidFFIType(resultType) || paramTypes.some(t => !isValidFFIType(t))) {
        diagnostics.push({ message: `Unknown FFI type at line ${i+1}` });
        continue;
      }
      if (paramTypes.includes('void')) {
        diagnostics.push({ message: `void cannot be a parameter type at line ${i+1}` });
        continue;
      }

      const signature: ForeignSignature = { params: paramTypes as any, result: resultType as any };
      const imp: ForeignImport = {
        kind: 'ForeignImport',
        target: 'cpp',
        name: { kind: 'Identifier', name: localName },
        symbol,
        signature
      };
      currentModule.declarations.push(imp);
      continue;
    }

    const declMatch = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$/);
    if (declMatch && currentModule) {
      const name = declMatch[1];
      const valueStr = declMatch[2].trim();
      const span: Span = { file: filename, start: i, end: i };

      let value: Expression;
      if (valueStr === 'true' || valueStr === 'false') {
        value = { kind: 'Literal', value: valueStr === 'true', span };
      } else if (!isNaN(Number(valueStr))) {
        value = { kind: 'Literal', value: Number(valueStr), span };
      } else if (valueStr.startsWith('"') && valueStr.endsWith('"')) {
        value = { kind: 'Literal', value: valueStr.slice(1, -1), span };
      } else if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(valueStr)) {
        value = { kind: 'Identifier', name: valueStr, span };
      } else {
        const callMatch = valueStr.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)$/);
        if (callMatch) {
          const callee = { kind: 'Identifier' as const, name: callMatch[1] };
          const argsStr = callMatch[2].trim();
          const args: Expression[] = argsStr.length === 0 ? [] : argsStr.split(',').map(s => {
            const t = s.trim();
            if (t === 'true' || t === 'false') return { kind: 'Literal' as const, value: t === 'true' };
            if (!isNaN(Number(t))) return { kind: 'Literal' as const, value: Number(t) };
            if (t.startsWith('"') && t.endsWith('"')) return { kind: 'Literal' as const, value: t.slice(1, -1) };
            return { kind: 'Identifier' as const, name: t };
          });
          value = { kind: 'CallExpression' as const, callee, arguments: args, span };
        } else {
          diagnostics.push({ message: `Invalid expression at line ${i+1}` });
          continue;
        }
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

  if (currentModule) modules.push(currentModule);

  return {
    program: diagnostics.length === 0 ? { kind: 'Program', modules } : undefined,
    diagnostics
  };
}
