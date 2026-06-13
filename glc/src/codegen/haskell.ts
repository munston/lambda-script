import { Program } from '../core/program';
import { Declaration, ForeignImport, CallExpression, Literal, FunctionDeclaration } from '../core/ast';

export function emitHaskell(program: Program): string {
  let out = '';
  let needsCString = false;

  for (const mod of program.modules) {
    out += `-- Module: ${mod.name}\n\n`;

    for (const item of mod.declarations) {
      if (item.kind === 'ForeignImport') {
        const f = item as ForeignImport;
        if (f.signature.params.includes('string') || f.signature.result === 'string') needsCString = true;
        const params = f.signature.params.map(t => mapHaskellType(t)).join(' -> ');
        const ret = mapHaskellType(f.signature.result);
        out += `foreign import ccall "${f.symbol}" ${f.name.name} :: ${params} -> IO ${ret}\n\n`;
      }
    }

    for (const item of mod.declarations) {
      if (item.kind === 'FunctionDeclaration') {
        const fn = item as FunctionDeclaration;
        const params = fn.signature.params.map(t => mapHaskellType(t));
        const sig = [...params, mapHaskellType(fn.signature.result)].join(' -> ');
        out += `${fn.name.name} :: ${sig}\n`;
        out += `${fn.name.name} ${fn.params.map(p => p.name).join(' ')} = ${emitHaskellExpr(fn.body)}\n\n`;
      }
      if (item.kind === 'Declaration') {
        const d = item as Declaration;
        if (d.value.kind === 'CallExpression') {
          const call = d.value as CallExpression;
          const foreign = mod.declarations.find(f => f.kind === 'ForeignImport' && f.name.name === call.callee.name) as ForeignImport | undefined;
          const retType = foreign ? mapHaskellType(foreign.signature.result) : 'Int';
          out += `${d.name.name} :: IO ${retType}\n`;
          if (foreign && foreign.signature.params.includes('string') && isStringLiteral(call.arguments[0])) {
            out += `${d.name.name} = withCString ${JSON.stringify(call.arguments[0].value)} ${call.callee.name}\n\n`;
          } else {
            const args = call.arguments.map(a => emitHaskellExpr(a)).join(' ');
            out += `${d.name.name} = ${call.callee.name} ${args}\n\n`;
          }
        } else {
          out += `${d.name.name} = ${emitHaskellExpr(d.value)}\n\n`;
        }
      }
    }
  }

  if (needsCString) {
    out = `import Foreign.C.String (CString, withCString)

${out}`;
  }
  return out.trim();
}

function isStringLiteral(e: any): e is Literal {
  return e && e.kind === 'Literal' && typeof e.value === 'string';
}

function mapHaskellType(t: string): string {
  if (t === 'i32') return 'Int';
  if (t === 'f64') return 'Double';
  if (t === 'bool') return 'Bool';
  if (t === 'string') return 'CString';
  return '()';
}

function emitHaskellExpr(e: any): string {
  if (e.kind === 'Literal') {
    if (typeof e.value === 'boolean') return e.value ? 'True' : 'False';
    if (typeof e.value === 'string') return JSON.stringify(e.value);
    return String(e.value);
  }
  if (e.kind === 'Identifier') return e.name;
  if (e.kind === 'CallExpression') {
    const args = e.arguments.map((arg: any) => {
      const emitted = emitHaskellExpr(arg);
      if (arg.kind === 'Literal' || arg.kind === 'Identifier') return emitted;
      return `(${emitted})`;
    }).join(' ');
    return args.length > 0 ? `${e.callee.name} ${args}` : e.callee.name;
  }
  if (e.kind === 'BinaryExpression') return `(${emitHaskellExpr(e.left)} ${e.operator} ${emitHaskellExpr(e.right)})`;
  if (e.kind === 'IfExpression') return `(if ${emitHaskellExpr(e.condition)} then ${emitHaskellExpr(e.thenBranch)} else ${emitHaskellExpr(e.elseBranch)})`;
  if (e.kind === 'LetExpression') return `(let ${e.name.name} = ${emitHaskellExpr(e.value)} in ${emitHaskellExpr(e.body)})`;
  return '/* unsupported */';
}
