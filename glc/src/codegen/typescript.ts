import { Program } from '../core/program';
import { Declaration, ForeignImport, CallExpression, FunctionDeclaration } from '../core/ast';

export function emitTypeScript(program: Program): string {
  const hasFFI = program.modules.some(m => m.declarations.some(d => d.kind === 'ForeignImport'));

  let out = hasFFI ? `import { CppForeignRuntime } from '../runtime/cppForeign';

` : '';

  for (const mod of program.modules) {
    const foreignNames = new Set(mod.declarations.filter(d => d.kind === 'ForeignImport').map(d => d.name.name));
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

`;
      }
    }

    for (const item of mod.declarations) {
      if (item.kind === 'FunctionDeclaration') {
        const fn = item as FunctionDeclaration;
        const params = fn.params.map((p, i) => `${p.name}: ${mapTsType(fn.signature.params[i])}`).join(', ');
        out += `export function ${fn.name.name}(${params}): ${mapTsType(fn.signature.result)} {
`;
        out += `  return ${emitExpr(fn.body)};
`;
        out += `}

`;
      }
      if (item.kind === 'Declaration') {
        const d = item as Declaration;
        if (d.value.kind === 'CallExpression' && foreignNames.has((d.value as CallExpression).callee.name)) {
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
  return 'unknown';
}

function expressionKind(e: any): string {
  if (e && typeof e.kind === 'string') return e.kind;
  return typeof e;
}

function emitExpr(e: any): string {
  if (e.kind === 'Literal') return JSON.stringify(e.value);
  if (e.kind === 'Identifier') return e.name;
  if (e.kind === 'CallExpression') {
    const c = e;
    return `${c.callee.name}(${c.arguments.map(emitExpr).join(', ')})`;
  }
  if (e.kind === 'BinaryExpression') return `(${emitExpr(e.left)} ${e.operator} ${emitExpr(e.right)})`;
  if (e.kind === 'IfExpression') return `(${emitExpr(e.condition)} ? ${emitExpr(e.thenBranch)} : ${emitExpr(e.elseBranch)})`;
  if (e.kind === 'LetExpression') return `(() => { const ${e.name.name} = ${emitExpr(e.value)}; return ${emitExpr(e.body)}; })()`;
  throw new Error(`TypeScript backend unsupported expression kind: ${expressionKind(e)}`);
}
