import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitTypeScript } from '../src/codegen/typescript';
import { emitHaskell } from '../src/codegen/haskell';
import * as fs from 'fs';
import assert from 'node:assert/strict';

function main() {
  const source = fs.readFileSync('examples/hello.ls', 'utf8');
  const program = parse(source, 'examples/hello.ls');

  const check = checkProgram(program);
  assert.strictEqual(check.diagnostics.length, 0);

  const ts = emitTypeScript(program);
  const hs = emitHaskell(program);

  assert.ok(ts.includes('export const answer = 42'));
  assert.ok(hs.includes('answer = 42'));
  assert.ok(hs.includes('flag = True'));
  assert.ok(!hs.includes('flag = true'));

  console.log('Smoke test passed');
}

main();
