import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitTypeScript } from '../src/codegen/typescript';
import { emitHaskell } from '../src/codegen/haskell';
import { runLsc } from '../src/cli/lsc';
import * as fs from 'fs';
import path from 'path';
import assert from 'node:assert/strict';

interface FixtureExpectation {
  file: string;
  tsIncludes: string[];
  hsIncludes: string[];
}

function checkFixture(fixture: FixtureExpectation) {
  const fixturePath = path.resolve(__dirname, '../../..', fixture.file);
  const src = fs.readFileSync(fixturePath, 'utf8');
  const pr = parse(src, fixturePath);
  assert.strictEqual(pr.diagnostics.length, 0, `${fixture.file} parse diagnostics`);
  const c = checkProgram(pr.program!);
  assert.strictEqual(c.diagnostics.length, 0, `${fixture.file} check diagnostics`);
  const ts = emitTypeScript(pr.program!);
  const hs = emitHaskell(pr.program!);
  for (const expected of fixture.tsIncludes) {
    assert.ok(ts.includes(expected), `${fixture.file} TypeScript output should include ${expected}`);
  }
  for (const expected of fixture.hsIncludes) {
    assert.ok(hs.includes(expected), `${fixture.file} Haskell output should include ${expected}`);
  }
  const originalError = console.error;
  try {
    console.error = () => {};
    assert.strictEqual(runLsc(['emit', fixturePath, '--target', 'py']), 1, `${fixture.file} should reject py target`);
    assert.strictEqual(runLsc(['emit', fixturePath, '--target', 'python']), 1, `${fixture.file} should reject python target`);
  } finally {
    console.error = originalError;
  }
}

function main() {
  const fixtures: FixtureExpectation[] = [
    {
      file: 'examples/hello.ls',
      tsIncludes: ['export const answer = 42', 'export const name = "lambda"', 'export const flag = true'],
      hsIncludes: ['answer = 42', 'name = "lambda"', 'flag = True'],
    },
    {
      file: 'examples/core/core0_values.ls',
      tsIncludes: ['export const answer = 42', 'export const ratio = 3.5', 'export const flag = true'],
      hsIncludes: ['answer = 42', 'ratio = 3.5', 'flag = True'],
    },
    {
      file: 'examples/core/core0_ffi.ls',
      tsIncludes: ['export function add_i32', "symbol: 'ls_add_i32'", 'export function answer(runtime: CppForeignRuntime)'],
      hsIncludes: ['foreign import ccall "ls_add_i32" add_i32', 'answer :: IO Int', 'scaled :: IO Double'],
    },
  ];
  for (const fixture of fixtures) checkFixture(fixture);
  console.log('Smoke test passed');
}

main();
