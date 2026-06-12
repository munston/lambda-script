import { Program, Module } from '../core/program';
import { Declaration, Expression } from '../core/ast';

/**
 * Very minimal declaration-only parser.
 * Supports:
 *   module Name
 *   name = 42
 *   name = "hello"
 *   name = true
 */
export function parse(source: string, filename = 'input.ls'): Program {
  const lines = source.split(/\r?\n/);
  let currentModule: Module | null = null;
  const modules: Module[] = [];

  for (let rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith('//')) continue;

    // module Name
    const moduleMatch = line.match(/^module\s+([A-Za-z_][A-Za-z0-9_]*)$/);
    if (moduleMatch) {
      if (currentModule) modules.push(currentModule);
      currentModule = {
        kind: 'Module',
        name: moduleMatch[1],
        declarations: [],
      };
      continue;
    }

    // name = value
    const declMatch = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$/);
    if (declMatch && currentModule) {
      const name = declMatch[1];
      const valueStr = declMatch[2].trim();

      let value: Expression;

      if (valueStr === 'true' || valueStr === 'false') {
        value = { kind: 'Literal', value: valueStr === 'true' };
      } else if (!isNaN(Number(valueStr))) {
        value = { kind: 'Literal', value: Number(valueStr) };
      } else if (valueStr.startsWith('"') && valueStr.endsWith('"')) {
        value = { kind: 'Literal', value: valueStr.slice(1, -1) };
      } else {
        value = { kind: 'Identifier', name: valueStr };
      }

      const decl: Declaration = {
        kind: 'Declaration',
        name: { kind: 'Identifier', name },
        value,
      };

      currentModule.declarations.push(decl);
      continue;
    }
  }

  if (currentModule) modules.push(currentModule);

  return {
    kind: 'Program',
    modules,
  };
}
