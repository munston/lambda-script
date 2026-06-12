import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitTypeScript } from '../src/codegen/typescript';
import { emitHaskell } from '../src/codegen/haskell';
import { runLsc } from '../src/cli/lsc';
import * as fs from 'fs';
import path from 'path';
import assert from 'node:assert/strict';

function main() {
  const helloPath = path.resolve(__dirname, '../../../examples/hello.ls');
  const src = fs.readFileSync(helloPath, 'utf8');
  const pr = parse(src, helloPath);
  assert.strictEqual(pr.diagnostics.length, 0);
  const c = checkProgram(pr.program!);
  assert.strictEqual(c.diagnostics.length, 0);
  const ts = emitTypeScript(pr.program!);
  const hs = emitHaskell(pr.program!);
  assert.ok(ts.includes('export const answer = 42'));
  assert.ok(hs.includes('answer = 42'));
  assert.ok(hs.includes('flag = True'));
  const originalError = console.error;
  try {
    console.error = () => {};
    assert.strictEqual(runLsc(['emit', helloPath, '--target', 'py']), 1);
    assert.strictEqual(runLsc(['emit', helloPath, '--target', 'python']), 1);
  } finally {
    console.error = originalError;
  }
  console.log('Smoke test passed');
}

main();
