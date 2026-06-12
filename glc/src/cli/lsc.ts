import { parse } from '../parser';
import { checkProgram } from '../core/check';
import { emitTypeScript } from '../codegen/typescript';
import { emitHaskell } from '../codegen/haskell';
import * as fs from 'fs';

export function runLsc(args: string[]): number {
  if (args.length === 0) {
    console.log(`Usage:
  lsc parse <file.ls> [--json]
  lsc check <file.ls>
  lsc emit <file.ls> --target ts|hs [--out <file>]

Targets are TypeScript and Haskell only. Python emission is unsupported by design.
`);
    return 1;
  }

  const command = args[0];
  const file = args[1];

  if (!file || !fs.existsSync(file)) {
    console.error('Error: file not found');
    return 1;
  }

  const source = fs.readFileSync(file, 'utf8');
  const parseResult = parse(source, file);

  if (parseResult.diagnostics.length > 0) {
    console.error('Parse errors:');
    parseResult.diagnostics.forEach(d => console.error(`  ${d.message}`));
    return 1;
  }

  const program = parseResult.program!;

  if (command === 'parse') {
    if (args.includes('--json')) {
      console.log(JSON.stringify(program, null, 2));
    } else {
      console.dir(program, { depth: null });
    }
    return 0;
  }

  if (command === 'check') {
    const checkResult = checkProgram(program);
    if (checkResult.diagnostics.length > 0) {
      console.error('Check diagnostics:');
      checkResult.diagnostics.forEach(d => console.error(`  ${d.message}`));
      return 1;
    }
    console.log('OK: no diagnostics');
    return 0;
  }

  if (command === 'emit') {
    const checkResult = checkProgram(program);
    if (checkResult.diagnostics.length > 0) {
      console.error('Check diagnostics:');
      checkResult.diagnostics.forEach(d => console.error(`  ${d.message}`));
      return 1;
    }

    const targetIdx = args.indexOf('--target');
    const target = targetIdx !== -1 ? args[targetIdx + 1] : 'ts';

    const outIdx = args.indexOf('--out');
    const outFile = outIdx !== -1 ? args[outIdx + 1] : null;

    let output: string;
    if (target === 'ts') {
      output = emitTypeScript(program);
    } else if (target === 'hs') {
      output = emitHaskell(program);
    } else if (target === 'py' || target === 'python') {
      console.error('Python emission is unsupported by design. glc emits TypeScript or Haskell only.');
      return 1;
    } else {
      console.error(`Unknown target: ${target}`);
      return 1;
    }

    if (outFile) {
      fs.writeFileSync(outFile, output);
      console.log(`Wrote ${outFile}`);
    } else {
      console.log(output);
    }
    return 0;
  }

  console.log('Unknown command');
  return 1;
}
