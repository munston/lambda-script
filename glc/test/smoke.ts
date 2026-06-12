import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitTypeScript } from '../src/codegen/typescript';
import { emitHaskell } from '../src/codegen/haskell';
import { emitPython } from '../src/codegen/python';
import * as fs from 'fs';
import path from 'path';
import assert from 'node:assert/strict';

function main() {
  const helloPath = path.resolve(__dirname, '../../../examples/hello.ls');
  const ffiPath = path.resolve(__dirname, '../../../examples/ffi_cpp.ls');

  // v0 hello.ls
  {
    const src = fs.readFileSync(helloPath, 'utf8');
    const pr = parse(src, helloPath);
    assert.strictEqual(pr.diagnostics.length, 0);
    const c = checkProgram(pr.program!);
    assert.strictEqual(c.diagnostics.length, 0);

    const ts = emitTypeScript(pr.program!);
    const hs = emitHaskell(pr.program!);
    const py = emitPython(pr.program!);
    assert.ok(ts.includes('export const answer = 42'));
    assert.ok(hs.includes('answer = 42'));
    assert.ok(hs.includes('flag = True'));
    assert.ok(py.includes('answer = 42'));
    assert.ok(py.includes('flag = True'));
  }

  // FFI
  {
    const src = fs.readFileSync(ffiPath, 'utf8');
    const pr = parse(src, ffiPath);
    assert.strictEqual(pr.diagnostics.length, 0);
    const c = checkProgram(pr.program!);
    assert.strictEqual(c.diagnostics.length, 0);

    const ts = emitTypeScript(pr.program!);
    const hs = emitHaskell(pr.program!);
    const py = emitPython(pr.program!);

    assert.ok(ts.includes('CppForeignRuntime'));
    assert.ok(ts.includes('export function add_i32'));
    assert.ok(ts.includes("symbol: 'ls_add_i32'"));
    assert.ok(hs.includes('foreign import ccall "ls_add_i32"'));
    assert.ok(hs.includes('foreign import ccall "ls_mul_f64"'));
    assert.ok(hs.includes('foreign import ccall "ls_log_message"'));
    assert.ok(py.includes('def add_i32(arg0, arg1):'));
    assert.ok(py.includes('foreign cpp symbol ls_add_i32 is not bound in Python output'));
  }

  // Negative FFI cases
  {
    const badType = `module Bad
foreign cpp x : nope -> i32 = "x"`;
    const pr1 = parse(badType, 'bad.ls');
    assert.ok(pr1.diagnostics.length > 0, 'Invalid FFI type should produce diagnostics');

    const badArity = `module Bad
foreign cpp add_i32 : i32 -> i32 -> i32 = "ls_add_i32"
answer = add_i32(1)`;
    const pr2 = parse(badArity, 'bad.ls');
    const c2 = checkProgram(pr2.program!);
    assert.ok(c2.diagnostics.length > 0, 'Wrong argument count should produce diagnostics');

    const badLiteral = `module Bad
foreign cpp add_i32 : i32 -> i32 -> i32 = "ls_add_i32"
answer = add_i32("bad", 2)`;
    const pr3 = parse(badLiteral, 'bad.ls');
    const c3 = checkProgram(pr3.program!);
    assert.ok(c3.diagnostics.length > 0, 'Wrong literal type should produce diagnostics');
  }

  console.log('Smoke test passed');
}

main();
