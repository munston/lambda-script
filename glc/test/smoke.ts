import { parse } from '../src/parser';
import { checkProgram } from '../src/core/check';
import { emitTypeScript } from '../src/codegen/typescript';
import { emitHaskell } from '../src/codegen/haskell';
import * as fs from 'fs';
import path from 'path';
import assert from 'node:assert/strict';

function main() {
  const examplePath = path.resolve(__dirname, '../../../examples/hello.ls');

  // Positive case
  const source = fs.readFileSync(examplePath, 'utf8');
  const parseResult = parse(source, examplePath);

  assert.strictEqual(parseResult.diagnostics.length, 0);

  const program = parseResult.program!;
  const check = checkProgram(program);
  assert.strictEqual(check.diagnostics.length, 0);

  const ts = emitTypeScript(program);
  const hs = emitHaskell(program);

  assert.ok(ts.includes('export const answer = 42'));
  assert.ok(ts.includes('export const flag = true'));
  assert.ok(hs.includes('answer = 42'));
  assert.ok(hs.includes('flag = True'));
  assert.ok(!hs.includes('flag = true'));

  // Negative case
  const badSource = 'module Bad
foo = 1
bar = print hello';
  const badResult = parse(badSource, 'bad.ls');
  assert.ok(badResult.diagnostics.length > 0);

  console.log('Smoke test passed');
}

main();
