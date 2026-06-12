import { Program } from '../core/program';
import { Declaration, ForeignImport, CallExpression } from '../core/ast';

export function emitTypeScript(program: Program): string {
  const hasFFI = program.modules.some(m => m.declarations.some(d => d.kind === 'ForeignImport'));

  let out = hasFFI ? `import { CppForeignRuntime } from '../runtime/cppForeign';

` : '';

  for (const mod of program.modules) {
    out += `// Module: ${mod.name}\n\n`;

    for (const item of mod.declarations) {
      if (item.kind === 'ForeignImport') {
        const f = item as ForeignImport;
        const params = f.signature.params.map((t, i) => `arg${i}: ${mapTsType(t)}`).join(', ');
        const ret = mapTsType(f.signature.result);
        out += `export function ${f.name.name}(runtime: CppForeignRuntime, ${params}): ${ret} {
`;
        out += `  return runtime.call({ symbol: '${f.symbol}', args: [${f.signature.params.map((_,i)=>`arg${i}`).join(', ')}] }) as ${ret};
`;
        out += `}
\n`;
      }
    }

    for (const item of mod.declarations) {
      if (item.kind === 'Declaration') {
        const d = item as Declaration;
        if (d.value.kind === 'CallExpression') {
          const call = d.value as CallExpression;
          const args = call.arguments.map(a => emitExpr(a)).join(', ');
          out += `export function ${d.name.name}(runtime: CppForeignRuntime) {
`;
          out += `  return ${call.callee.name}(runtime, ${args});
`;
          out += `}

`;
        } else {
          out += `export const ${d.name.name} = ${emitExpr(d.value)};

`;
        }
      }
    }
  }
  return out.trim();
}

function mapTsType(t: string): string {
  if (t === 'i32' || t === 'f64') return 'number';
  if (t === 'bool') return 'boolean';
  if (t === 'string') return 'string';
  if (t === 'void') return 'null';
  return 'any';
}

function emitExpr(e: any): string {
  if (e.kind === 'Literal') return JSON.stringify(e.value);
  if (e.kind === 'Identifier') return e.name;
  if (e.kind === 'CallExpression') {
    const c = e;
    return `${c.callee.name}(${c.arguments.map(emitExpr).join(', ')})`;
  }
  return '/* unsupported */';
}
