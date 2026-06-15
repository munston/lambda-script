import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitHaskell } from '../src/codegen/haskell';
import { emitTypeScript } from '../src/codegen/typescript';
import * as fs from 'fs';
import path from 'path';
import assert from 'node:assert/strict';

const fixturePath = path.resolve(__dirname, '../../..', 'examples/gpt/gpt2_local_scalar.ls');
const source = fs.readFileSync(fixturePath, 'utf8');
const parsed = parse(source, fixturePath);
assert.strictEqual(parsed.diagnostics.length, 0, 'local GPT scalar fixture should parse');

const checked = checkProgram(parsed.program!);
assert.strictEqual(checked.diagnostics.length, 0, 'local GPT scalar fixture should check');

const hs = emitHaskell(parsed.program!);
assert.ok(hs.includes('-- Module: Gpt2LocalScalar'), 'Haskell output should preserve module marker');
assert.ok(hs.includes('max2 :: Double -> Double -> Double'), 'Haskell output should emit max2 signature');
assert.ok(hs.includes('exp_approx :: Double -> Double'), 'Haskell output should emit exp approximation signature');
assert.ok(hs.includes('softmax2_left :: Double -> Double -> Double'), 'Haskell output should emit scalar softmax signature');
assert.ok(hs.includes('causal_mask :: Int -> Int -> Double'), 'Haskell output should emit causal mask signature');
assert.ok(hs.includes('causal_mask i j = (if (i < j) then -10000000000 else 0)'), 'Haskell output should emit causal mask branch');
assert.ok(hs.includes('gelu_cubic :: Double -> Double'), 'Haskell output should emit gelu scalar signature');
assert.ok(hs.includes('rsqrt3 :: Double -> Double'), 'Haskell output should emit reciprocal square-root approximation signature');
assert.ok(hs.includes('linear2 :: Double -> Double -> Double -> Double -> Double -> Double'), 'Haskell output should emit scalar linear kernel signature');

const ts = emitTypeScript(parsed.program!);
assert.ok(ts.includes('export function max2(a: number, b: number): number'), 'TypeScript output should emit max2');
assert.ok(ts.includes('export function softmax2_left(a: number, b: number): number'), 'TypeScript output should emit scalar softmax');
assert.ok(ts.includes('export function layer_norm2_left(x0: number, x1: number, gamma: number, beta: number, epsilon: number): number'), 'TypeScript output should emit scalar layer norm');

console.log('Local GPT scalar emission smoke passed');
