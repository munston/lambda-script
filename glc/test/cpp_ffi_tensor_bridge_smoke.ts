import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitHaskell } from '../src/codegen/haskell';
import { emitTypeScript } from '../src/codegen/typescript';
import * as fs from 'fs';
import path from 'path';
import assert from 'node:assert/strict';

const fixturePath = path.resolve(__dirname, '../../..', 'examples/core/core0_ffi_tensor_handles.ls');
const source = fs.readFileSync(fixturePath, 'utf8');
const parsed = parse(source, fixturePath);
assert.strictEqual(parsed.diagnostics.length, 0, 'C++ FFI tensor-handle fixture should parse');

const checked = checkProgram(parsed.program!);
assert.strictEqual(checked.diagnostics.length, 0, 'C++ FFI tensor-handle fixture should check');

const hs = emitHaskell(parsed.program!);
assert.ok(hs.includes('foreign import ccall "ls_gpt_alloc_f64_buffer" gpt_alloc_f64_buffer :: Int -> IO Int'), 'Haskell output should emit allocation handle import');
assert.ok(hs.includes('foreign import ccall "ls_gpt_free_handle" gpt_free_handle :: Int -> IO ()'), 'Haskell output should emit free-handle import');
assert.ok(hs.includes('foreign import ccall "ls_gpt_read_f64" gpt_read_f64 :: Int -> Int -> IO Double'), 'Haskell output should emit read import');
assert.ok(hs.includes('foreign import ccall "ls_gpt_write_f64" gpt_write_f64 :: Int -> Int -> Double -> IO ()'), 'Haskell output should emit write import');
assert.ok(hs.includes('foreign import ccall "ls_gpt_dot_f64" gpt_dot_f64 :: Int -> Int -> Int -> IO Double'), 'Haskell output should emit dot import');
assert.ok(hs.includes('sample_buffer :: IO Int'), 'Haskell output should type allocation call as IO Int');
assert.ok(hs.includes('sample_dot :: IO Double'), 'Haskell output should type dot call as IO Double');
assert.ok(hs.includes('cleanup :: IO ()'), 'Haskell output should type cleanup call as IO ()');

const ts = emitTypeScript(parsed.program!);
assert.ok(ts.includes('export function gpt_alloc_f64_buffer(runtime: CppForeignRuntime, arg0: number): number'), 'TypeScript output should emit allocation wrapper');
assert.ok(ts.includes('export function gpt_write_f64(runtime: CppForeignRuntime, arg0: number, arg1: number, arg2: number): null'), 'TypeScript output should emit write wrapper');
assert.ok(ts.includes("symbol: 'ls_gpt_dot_f64'"), 'TypeScript output should include dot symbol');
assert.ok(ts.includes('export function sample_dot(runtime: CppForeignRuntime)'), 'TypeScript output should expose sample dot call');

console.log('C++ FFI tensor bridge smoke passed');
