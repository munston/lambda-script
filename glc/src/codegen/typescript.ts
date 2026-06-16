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
        out += `  return ${emitExpr(fn.body, foreignNames)};
`;
        out += `}

`;
      }
      if (item.kind === 'Declaration') {
        const d = item as Declaration;
        if (d.value.kind === 'CallExpression' && foreignNames.has((d.value as CallExpression).callee.name)) {
          const call = d.value as CallExpression;
          const args = call.arguments.map(a => emitExpr(a, foreignNames)).join(', ');
          out += `export function ${d.name.name}(runtime: CppForeignRuntime) {
`;
          out += `  return ${call.callee.name}(runtime, ${args});
`;
          out += `}

`;
        } else {
          out += `export const ${d.name.name} = ${emitExpr(d.value, foreignNames)};
`;
        }
      }
    }
  }
  return out.trim();
}

function mapTsType(t: string): string {
  if (t === 'i32' || t === 'f64' || t === 'handle' || t === 'f64buf' || t === 'i32buf') return 'number';
  if (t === 'bool') return 'boolean';
  if (t === 'string') return 'string';
  if (t === 'void') return 'null';
  return 'unknown';
}

function expressionKind(e: any): string {
  if (e && typeof e.kind === 'string') return e.kind;
  return typeof e;
}

function emitExpr(e: any, foreignNames = new Set<string>()): string {
  if (e.kind === 'Literal') return JSON.stringify(e.value);
  if (e.kind === 'Identifier') return e.name;
  if (e.kind === 'CallExpression') {
    const c = e;
    if (foreignNames.has(c.callee.name)) throw new Error(`TypeScript backend unsupported foreign call placement: ${c.callee.name}`);
    return `${c.callee.name}(${c.arguments.map((arg: any) => emitExpr(arg, foreignNames)).join(', ')})`;
  }
  if (e.kind === 'UnaryExpression') return `(!${emitExpr(e.operand, foreignNames)})`;
  if (e.kind === 'BinaryExpression') return `(${emitExpr(e.left, foreignNames)} ${e.operator} ${emitExpr(e.right, foreignNames)})`;
  if (e.kind === 'IfExpression') return `(${emitExpr(e.condition, foreignNames)} ? ${emitExpr(e.thenBranch, foreignNames)} : ${emitExpr(e.elseBranch, foreignNames)})`;
  if (e.kind === 'LetExpression') return `(() => { const ${e.name.name} = ${emitExpr(e.value, foreignNames)}; return ${emitExpr(e.body, foreignNames)}; })()`;
  throw new Error(`TypeScript backend unsupported expression kind: ${expressionKind(e)}`);
}
