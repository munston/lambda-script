import { Program, Module } from '../core/program';
import { Declaration, Expression, Span } from '../core/ast';
import { Diagnostic } from '../core/diagnostic';

export interface ParseResult {
  program?: Program;
  diagnostics: Diagnostic[];
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

    const declMatch = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$/);
    if (declMatch) {
      if (!currentModule) {
        diagnostics.push({
          message: 'Declaration before module declaration',
          span: { file: filename, start: i, end: i },
        });
        continue;
      }

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
        diagnostics.push({
          message: `Invalid value: ${valueStr}`,
          span,
        });
        continue;
      }

      const decl: Declaration = {
        kind: 'Declaration',
        name: { kind: 'Identifier', name, span },
        value,
      };
      currentModule.declarations.push(decl);
      continue;
    }

    diagnostics.push({
      message: `Invalid line: ${rawLine.trim()}`,
      span: { file: filename, start: i, end: i },
    });
  }

  if (currentModule) modules.push(currentModule);

  return {
    program: diagnostics.length === 0 ? { kind: 'Program', modules } : undefined,
    diagnostics,
  };
}
