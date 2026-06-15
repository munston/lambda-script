import { Program } from '../core/program';
import { Declaration, ForeignImport, CallExpression, Literal, FunctionDeclaration } from '../core/ast';

export function emitHaskell(program: Program): string {
  let out = '';
  let needsCString = false;
  let needsPtr = false;
  let needsCTypes = false;

  for (const mod of program.modules) {
    const foreignNames = new Set(mod.declarations.filter(d => d.kind === 'ForeignImport').map(d => d.name.name));
    out += `-- Module: ${mod.name}\n\n`;

    for (const item of mod.declarations) {
      if (item.kind === 'ForeignImport') {
        const f = item as ForeignImport;
        const allTypes = [...f.signature.params, f.signature.result];
        if (allTypes.includes('string')) needsCString = true;
        if (allTypes.some(t => ['handle', 'f64buf', 'i32buf'].includes(t))) needsPtr = true;
        if (allTypes.some(t => ['f64buf', 'i32buf'].includes(t))) needsCTypes = true;
        const params = f.signature.params.map(t => mapHaskellType(t)).join(' -> ');
        const ret = mapHaskellType(f.signature.result);
        out += `foreign import ccall "${f.symbol}" ${f.name.name} :: ${params} -> ${ioType(ret)}\n\n`;
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
        if (d.value.kind === 'CallExpression' && foreignNames.has((d.value as CallExpression).callee.name)) {
          const call = d.value as CallExpression;
          const foreign = mod.declarations.find(f => f.kind === 'ForeignImport' && f.name.name === call.callee.name) as ForeignImport | undefined;
          const retType = foreign ? mapHaskellType(foreign.signature.result) : 'Int';
          out += `${d.name.name} :: ${ioType(retType)}\n`;
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

  const imports: string[] = [];
  if (needsCString) imports.push('import Foreign.C.String (CString, withCString)');
  if (needsPtr) imports.push('import Foreign.Ptr (Ptr)');
  if (needsCTypes) imports.push('import Foreign.C.Types (CDouble, CInt)');
  if (imports.length > 0) out = `${imports.join('\n')}\n\n${out}`;
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
  if (t === 'handle') return 'Ptr ()';
  if (t === 'f64buf') return 'Ptr CDouble';
  if (t === 'i32buf') return 'Ptr CInt';
  return '()';
}

function ioType(t: string): string {
  return t.includes(' ') ? `IO (${t})` : `IO ${t}`;
}

function parenIfNeeded(s: string): string {
  return s.startsWith('(') && s.endsWith(')') ? s : `(${s})`;
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
      return parenIfNeeded(emitted);
    }).join(' ');
    return args.length > 0 ? `${e.callee.name} ${args}` : e.callee.name;
  }
  if (e.kind === 'BinaryExpression') return `(${emitHaskellExpr(e.left)} ${e.operator} ${emitHaskellExpr(e.right)})`;
  if (e.kind === 'IfExpression') return `(if ${emitHaskellExpr(e.condition)} then ${emitHaskellExpr(e.thenBranch)} else ${emitHaskellExpr(e.elseBranch)})`;
  if (e.kind === 'LetExpression') return `(let ${e.name.name} = ${emitHaskellExpr(e.value)} in ${emitHaskellExpr(e.body)})`;
  return '/* unsupported */';
}
