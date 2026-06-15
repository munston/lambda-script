import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitHaskell } from '../src/codegen/haskell';
import { emitTypeScript } from '../src/codegen/typescript';
import * as fs from 'fs';
import path from 'path';
import assert from 'node:assert/strict';

const fixturePath = path.resolve(__dirname, '../../..', 'examples/core/core0_ffi_typed_buffers.ls');
const source = fs.readFileSync(fixturePath, 'utf8');
const parsed = parse(source, fixturePath);
assert.strictEqual(parsed.diagnostics.length, 0, 'typed FFI buffer fixture should parse');

const checked = checkProgram(parsed.program!);
assert.strictEqual(checked.diagnostics.length, 0, 'typed FFI buffer fixture should check');

const hs = emitHaskell(parsed.program!);
assert.ok(hs.includes('import Foreign.C.String (CString, withCString)'), 'Haskell output should import CString support');
assert.ok(hs.includes('import Foreign.Ptr (Ptr)'), 'Haskell output should import Ptr');
assert.ok(hs.includes('import Foreign.C.Types (CDouble, CInt)'), 'Haskell output should import C numeric pointer types');
assert.ok(hs.includes('foreign import ccall "ls_gpt_alloc_f64_buffer" gpt_alloc_f64_buffer :: Int -> IO (Ptr CDouble)'), 'Haskell output should emit f64 buffer allocation');
assert.ok(hs.includes('foreign import ccall "ls_gpt_alloc_i32_buffer" gpt_alloc_i32_buffer :: Int -> IO (Ptr CInt)'), 'Haskell output should emit i32 buffer allocation');
assert.ok(hs.includes('foreign import ccall "ls_gpt_create_model" gpt_create_model :: CString -> IO (Ptr ())'), 'Haskell output should emit model handle creation');
assert.ok(hs.includes('foreign import ccall "ls_gpt_model_score" gpt_model_score :: Ptr () -> Ptr CInt -> Int -> IO Double'), 'Haskell output should emit typed model scoring');
assert.ok(hs.includes('weights :: IO (Ptr CDouble)'), 'Haskell output should type f64 buffer value');
assert.ok(hs.includes('tokens :: IO (Ptr CInt)'), 'Haskell output should type i32 buffer value');
assert.ok(hs.includes('model :: IO (Ptr ())'), 'Haskell output should type model handle value');
assert.ok(hs.includes('model = withCString "tiny-gpt" gpt_create_model'), 'Haskell output should handle string-to-CString model creation');
assert.ok(hs.includes('score :: IO Double'), 'Haskell output should type model score as IO Double');

const ts = emitTypeScript(parsed.program!);
assert.ok(ts.includes('export function gpt_alloc_f64_buffer(runtime: CppForeignRuntime, arg0: number): number'), 'TypeScript output should emit f64 buffer wrapper');
assert.ok(ts.includes('export function gpt_create_model(runtime: CppForeignRuntime, arg0: string): number'), 'TypeScript output should emit handle wrapper');
assert.ok(ts.includes('export function gpt_model_score(runtime: CppForeignRuntime, arg0: number, arg1: number, arg2: number): number'), 'TypeScript output should emit model score wrapper');
assert.ok(ts.includes("symbol: 'ls_gpt_model_score'"), 'TypeScript output should preserve model score symbol');

const badSource = `module BadTypedBuffers

foreign cpp read_i32 : i32buf -> i32 -> i32 = "read_i32"
foreign cpp alloc_f64 : i32 -> f64buf = "alloc_f64"

buf = alloc_f64(4)
bad = read_i32(buf, 0)
`;
const badParsed = parse(badSource, 'bad_typed_buffers.ls');
assert.strictEqual(badParsed.diagnostics.length, 0, 'bad typed-buffer fixture should parse');
const badChecked = checkProgram(badParsed.program!);
assert.ok(
  badChecked.diagnostics.some(d => d.message.includes('Argument 1 for read_i32 has type f64buf, expected i32buf')),
  `expected typed buffer mismatch, got ${badChecked.diagnostics.map(d => d.message).join('; ')}`
);

console.log('Typed C++ FFI buffer smoke passed');
