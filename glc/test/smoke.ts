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
  tsExcludes?: string[];
  hsExcludes?: string[];
  tsSnapshot?: string;
  hsSnapshot?: string;
}

function normalizeOutput(text: string): string {
  return text.replace(/\r\n/g, '\n').trim();
}

function readSnapshot(snapshot: string): string {
  const snapshotPath = path.resolve(__dirname, '../../..', snapshot);
  return normalizeOutput(fs.readFileSync(snapshotPath, 'utf8'));
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
  for (const rejected of fixture.tsExcludes ?? []) {
    assert.ok(!ts.includes(rejected), `${fixture.file} TypeScript output should not include ${rejected}`);
  }
  for (const rejected of fixture.hsExcludes ?? []) {
    assert.ok(!hs.includes(rejected), `${fixture.file} Haskell output should not include ${rejected}`);
  }
  if (fixture.tsSnapshot) {
    assert.strictEqual(normalizeOutput(ts), readSnapshot(fixture.tsSnapshot), `${fixture.file} TypeScript snapshot`);
  }
  if (fixture.hsSnapshot) {
    assert.strictEqual(normalizeOutput(hs), readSnapshot(fixture.hsSnapshot), `${fixture.file} Haskell snapshot`);
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

function checkFails(name: string, source: string, expected: string) {
  const pr = parse(source, `${name}.ls`);
  assert.strictEqual(pr.diagnostics.length, 0, `${name} should parse`);
  const c = checkProgram(pr.program!);
  assert.ok(c.diagnostics.some(d => d.message.includes(expected)), `${name} should report ${expected}, got ${c.diagnostics.map(d => d.message).join('; ')}`);
}

function parseFails(name: string, source: string, expected: string) {
  const pr = parse(source, `${name}.ls`);
  assert.ok(pr.diagnostics.some(d => d.message.includes(expected)), `${name} should report ${expected}, got ${pr.diagnostics.map(d => d.message).join('; ')}`);
}

function checkUnsupportedBackendErrors() {
  const badProgram: any = {
    kind: 'Program',
    modules: [
      {
        kind: 'Module',
        name: 'BadBackend',
        declarations: [
          {
            kind: 'Declaration',
            name: { kind: 'Identifier', name: 'bad' },
            value: { kind: 'MysteryExpression' },
          },
        ],
      },
    ],
  };

  assert.throws(
    () => emitTypeScript(badProgram),
    /TypeScript backend unsupported expression kind: MysteryExpression/,
    'TypeScript backend should reject unsupported expression kinds clearly',
  );
  assert.throws(
    () => emitHaskell(badProgram),
    /Haskell backend unsupported expression kind: MysteryExpression/,
    'Haskell backend should reject unsupported expression kinds clearly',
  );
}

function checkHaskellNotEqualEmission() {
  const source = `module Compare

is_not : i32 -> i32 -> bool
is_not x y = x != y
`;
  const pr = parse(source, 'not-equal.ls');
  assert.strictEqual(pr.diagnostics.length, 0, 'not-equal should parse');
  const c = checkProgram(pr.program!);
  assert.strictEqual(c.diagnostics.length, 0, `not-equal should check, got ${c.diagnostics.map(d => d.message).join('; ')}`);

  const ts = emitTypeScript(pr.program!);
  const hs = emitHaskell(pr.program!);
  assert.ok(ts.includes('return (x != y);'), 'TypeScript should preserve LambdaScript != as target-valid !=');
  assert.ok(hs.includes('is_not x y = (x /= y)'), 'Haskell should emit LambdaScript != as /=');
  assert.ok(!hs.includes('!='), 'Haskell output should not contain raw !=');
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
      tsIncludes: [
        'export function add_i32',
        "symbol: 'ls_add_i32'",
        'export function answer(runtime: CppForeignRuntime): number',
        'export function log_message(runtime: CppForeignRuntime, arg0: string): void',
        'export function done(runtime: CppForeignRuntime): void',
        '  log_message(runtime, "hello from Core-0");',
      ],
      hsIncludes: ['foreign import ccall "ls_add_i32" add_i32', 'answer :: IO Int', 'scaled :: IO Double', 'done :: IO ()'],
      tsExcludes: ['return log_message(runtime, "hello from Core-0");', ': null'],
    },
    {
      file: 'examples/core/core1_functions.ls',
      tsIncludes: ['export function add(x: number, y: number): number', 'export function max_i32(x: number, y: number): number', 'return ((n <= 1) ? 1 : (n * fact((n - 1))))'],
      hsIncludes: ['add :: Int -> Int -> Int', 'max_i32 :: Int -> Int -> Int', 'fact n = (if (n <= 1) then 1 else (n * fact (n - 1)))'],
    },
    {
      file: 'examples/core/core1_let.ls',
      tsIncludes: ['export function square_plus(x: number, y: number): number', 'const xx = (x * x); return (xx + y)', 'const below = (x < floor); return (below ? floor : x)'],
      hsIncludes: ['square_plus :: Int -> Int -> Int', 'square_plus x y = (let xx = (x * x) in (xx + y))', 'clamp_min floor x = (let below = (x < floor) in (if below then floor else x))'],
      tsSnapshot: 'glc/test/snapshots/core1_let.ts.snap',
      hsSnapshot: 'glc/test/snapshots/core1_let.hs.snap',
    },
    {
      file: 'examples/core/core1_pure_calls.ls',
      tsIncludes: ['export const total = add(1, 2)', 'export const chosen = max_i32(add(1, 1), 3)'],
      hsIncludes: ['total = add 1 2', 'chosen = max_i32 (add 1 1) 3'],
    },
  ];
  for (const fixture of fixtures) checkFixture(fixture);
  checkUnsupportedBackendErrors();
  checkHaskellNotEqualEmission();

  checkFails('unknown-variable', `module Bad\n\nf : i32 -> i32\nf x = y\n`, 'Unknown identifier: y');
  checkFails('wrong-arity', `module Bad\n\nadd : i32 -> i32 -> i32\nadd x y = x + y\nz = add(1)\n`, 'Wrong argument count for add');
  checkFails('wrong-argument-type', `module Bad\n\nadd : i32 -> i32 -> i32\nadd x y = x + y\nz = add(true, 1)\n`, 'Argument 1 for add has type bool, expected i32');
  checkFails('if-condition-type', `module Bad\n\nf : i32 -> i32\nf x = if x then 1 else 2\n`, 'If condition has type i32, expected bool');
  checkFails('if-branch-type', `module Bad\n\nf : i32 -> i32\nf x = if x < 1 then 1 else false\n`, 'If branches have different types: i32 and bool');
  checkFails('return-type', `module Bad\n\nf : i32 -> i32\nf x = false\n`, 'Function f returns bool, expected i32');
  checkFails('binary-type', `module Bad\n\nf : bool -> bool\nf x = x + true\n`, 'Operator + expects numeric operands');
  parseFails('dangling-signature', `module Bad\n\nf : i32 -> i32\n`, 'Dangling type signature for f');
  parseFails('duplicate-signature', `module Bad\n\nf : i32 -> i32\nf : i32 -> i32\nf x = x\n`, 'Duplicate type signature for f');
  console.log('Smoke test passed');
}

main();
