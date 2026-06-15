declare const require: any;
declare const process: any;
declare const __dirname: string;
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const root = path.resolve(__dirname, '..', '..');
function run(args: string[]): void {
  const proc = cp.spawnSync(process.execPath, args, { cwd: root, encoding: 'utf-8' });
  process.stdout.write(proc.stdout || '');
  process.stderr.write(proc.stderr || '');
  if (proc.status !== 0) throw new Error(`command failed: ${args.join(' ')}`);
}
function assertFile(p: string): void {
  if (!fs.existsSync(p) || fs.statSync(p).size <= 0) throw new Error(`missing or empty file: ${p}`);
}
const out = path.join(root, 'runs', 'smoke-image-metrics');
fs.rmSync(out, { recursive: true, force: true });
run(['dist/src/cli.js', 'version']);
run(['dist/src/cli.js', 'analyze', 'synthetic://smoke-a', '--out', path.join(out, 'analyze')]);
assertFile(path.join(out, 'analyze', 'report.json'));
assertFile(path.join(out, 'analyze', 'feature_fixture.json'));
run(['dist/src/cli.js', 'image-parametric-demo', '--out', path.join(out, 'parametric'), 'synthetic://smoke-a', 'synthetic://smoke-b']);
assertFile(path.join(out, 'parametric', 'image_parametric_report.json'));
assertFile(path.join(out, 'parametric', 'image_parametric_summary.txt'));
console.log('image-metrics TypeScript/C++ smoke passed');
