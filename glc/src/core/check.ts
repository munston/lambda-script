import { Program } from './program';
import { Diagnostic } from './diagnostic';
import { CallExpression, ForeignImport } from './ast';

export function checkProgram(program: Program): { diagnostics: Diagnostic[] } {
  const diagnostics: Diagnostic[] = [];
  const names = new Set<string>();

  for (const mod of program.modules) {
    names.clear();
    for (const item of mod.declarations) {
      const name = item.kind === 'Declaration' ? item.name.name : item.name.name;
      if (names.has(name)) diagnostics.push({ message: `Duplicate top-level name: ${name}` });
      names.add(name);
    }

    for (const item of mod.declarations) {
      if (item.kind === 'Declaration' && item.value.kind === 'CallExpression') {
        const call = item.value as CallExpression;
        const callee = call.callee.name;

        const foreign = mod.declarations.find(d =>
          d.kind === 'ForeignImport' && d.name.name === callee
        ) as ForeignImport | undefined;

        if (!foreign) {
          diagnostics.push({ message: `Unknown function: ${callee}` });
          continue;
        }

        if (call.arguments.length !== foreign.signature.params.length) {
          diagnostics.push({ message: `Wrong argument count for ${callee}` });
          continue;
        }

        for (let j = 0; j < call.arguments.length; j++) {
          const arg = call.arguments[j];
          const expected = foreign.signature.params[j];
          if (arg.kind === 'Literal') {
            const lit = arg as any;
            if (expected === 'i32' && typeof lit.value !== 'number') diagnostics.push({ message: `Expected i32 for arg ${j} of ${callee}` });
            if (expected === 'f64' && typeof lit.value !== 'number') diagnostics.push({ message: `Expected f64 for arg ${j} of ${callee}` });
            if (expected === 'bool' && typeof lit.value !== 'boolean') diagnostics.push({ message: `Expected bool for arg ${j} of ${callee}` });
            if (expected === 'string' && typeof lit.value !== 'string') diagnostics.push({ message: `Expected string for arg ${j} of ${callee}` });
          }
        }
      }
    }
  }
  return { diagnostics };
}
