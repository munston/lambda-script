import { Program } from '../core/program';
import { Declaration, ForeignImport, CallExpression, Literal, FunctionDeclaration } from '../core/ast';

export function emitHaskell(program: Program): string {
  let out = '';
  let needsCString = false;
  let needsPtr = false;
  let needsCDouble = false;
  let needsCInt = false;

  for (const mod of program.modules) {
    const foreignNames = new Set(mod.declarations.filter(d => d.kind === 'ForeignImport').map(d => d.name.name));
    out += `-- Module: ${mod.name}
`;

    for (const item of mod.declarations) {
      if (item.kind === 'ForeignImport') {
        const f = item as ForeignImport;
        const allTypes = [...f.signature.params, f.signature.result];
        if (allTypes.includes('string')) needsCString = true;
        if (allTypes.some(isPointerBackedType)) needsPtr = true;
        if (allTypes.includes('f64buf')) needsCDouble = true;
        if (allTypes.includes('i32buf')) needsCInt = true;
        const params = f.signature.params.map(t => mapHaskellType(t));
        const ret = mapHaskellIOResultType(f.signature.result);
        const sig = params.length > 0 ? `${params.join(' -> ')} -> IO ${ret}` : `IO ${ret}`;
        out += `foreign import ccall "${f.symbol}" ${f.name.name} :: ${sig}

`;
      }
    }

    for (const item of mod.declarations) {
      if (item.kind === 'FunctionDeclaration') {
        const fn = item as FunctionDeclaration;
        const params = fn.signature.params.map(t => mapHaskellType(t));
        const sig = [...params, mapHaskellType(fn.signature.result)].join(' -> ');
        out += `${fn.name.name} :: ${sig}
`;
        out += `${fn.name.name} ${fn.params.map(p => p.name).join(' ')} = ${emitHaskellExpr(fn.body, foreignNames)}

`;
      }
      if (item.kind === 'Declaration') {
        const d = item as Declaration;
        if (d.value.kind === 'CallExpression' && foreignNames.has((d.value as CallExpression).callee.name)) {
          const call = d.value as CallExpression;
          const foreign = mod.declarations.find(f => f.kind === 'ForeignImport' && f.name.name === call.callee.name) as ForeignImport | undefined;
          const retType = foreign ? mapHaskellIOResultType(foreign.signature.result) : 'Int';
          out += `${d.name.name} :: IO ${retType}
`;
          if (foreign && foreign.signature.params.includes('string') && isStringLiteral(call.arguments[0])) {
            out += `${d.name.name} = withCString ${JSON.stringify(call.arguments[0].value)} ${call.callee.name}

`;
          } else {
            const args = call.arguments.map(a => emitHaskellExpr(a, foreignNames)).join(' ');
            out += `${d.name.name} = ${call.callee.name} ${args}

`;
          }
        } else {
          out += `${d.name.name} = ${emitHaskellExpr(d.value, foreignNames)}

`;
        }
      }
    }
  }

  const imports: string[] = [];
  if (needsCString) imports.push('import Foreign.C.String (CString, withCString)');
  if (needsPtr) imports.push('import Foreign.Ptr (Ptr)');
  if (needsCDouble || needsCInt) {
    const types = [needsCDouble ? 'CDouble' : undefined, needsCInt ? 'CInt' : undefined].filter(Boolean).join(', ');
    imports.push(`import Foreign.C.Types (${types})`);
  }
  if (imports.length > 0) out = `${imports.join('\n')}

${out}`;
  return out.trim();
}

function isStringLiteral(e: any): e is Literal {
  return e && e.kind === 'Literal' && typeof e.value === 'string';
}

function isPointerBackedType(t: string): boolean {
  return t === 'handle' || t === 'f64buf' || t === 'i32buf';
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

function mapHaskellIOResultType(t: string): string {
  const mapped = mapHaskellType(t);
  return isPointerBackedType(t) ? `(${mapped})` : mapped;
}

function mapHaskellBinaryOperator(op: string): string {
  if (op === '!=') return '/=';
  return op;
}

function parenIfNeeded(s: string): string {
  return s.startsWith('(') && s.endsWith(')') ? s : `(${s})`;
}

function expressionKind(e: any): string {
  if (e && typeof e.kind === 'string') return e.kind;
  return typeof e;
}

function isAtomicHaskellOperand(e: any): boolean {
  return e.kind === 'Literal' || e.kind === 'Identifier';
}

function emitHaskellExpr(e: any, foreignNames = new Set<string>()): string {
  if (e.kind === 'Literal') {
    if (typeof e.value === 'boolean') return e.value ? 'True' : 'False';
    if (typeof e.value === 'string') return JSON.stringify(e.value);
    return String(e.value);
  }
  if (e.kind === 'Identifier') return e.name;
  if (e.kind === 'CallExpression') {
    if (foreignNames.has(e.callee.name)) throw new Error(`Haskell backend unsupported foreign call placement: ${e.callee.name}`);
    const args = e.arguments.map((arg: any) => {
      const emitted = emitHaskellExpr(arg, foreignNames);
      if (arg.kind === 'Literal' || arg.kind === 'Identifier') return emitted;
      return parenIfNeeded(emitted);
    }).join(' ');
    return args.length > 0 ? `${e.callee.name} ${args}` : e.callee.name;
  }
  if (e.kind === 'UnaryExpression') {
    const emitted = emitHaskellExpr(e.operand, foreignNames);
    return `not ${isAtomicHaskellOperand(e.operand) ? emitted : parenIfNeeded(emitted)}`;
  }
  if (e.kind === 'BinaryExpression') return `(${emitHaskellExpr(e.left, foreignNames)} ${mapHaskellBinaryOperator(e.operator)} ${emitHaskellExpr(e.right, foreignNames)})`;
  if (e.kind === 'IfExpression') return `(if ${emitHaskellExpr(e.condition, foreignNames)} then ${emitHaskellExpr(e.thenBranch, foreignNames)} else ${emitHaskellExpr(e.elseBranch, foreignNames)})`;
  if (e.kind === 'LetExpression') return `(let ${e.name.name} = ${emitHaskellExpr(e.value, foreignNames)} in ${emitHaskellExpr(e.body, foreignNames)})`;
  throw new Error(`Haskell backend unsupported expression kind: ${expressionKind(e)}`);
}
