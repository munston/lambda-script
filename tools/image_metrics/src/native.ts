declare const require: any;
declare const process: any;
declare const __dirname: string;
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

export interface NativeMetricResult { score: number; [key: string]: number; }
export interface AnalyzeImageRequest { imagePath: string; outDir: string; }
export interface StochasticUpdateRequest { imagePath: string; outDir: string; seed: number; trials: number; support: number; step: number; }

function ffiPath(): string { return path.resolve(__dirname, '..', '..', 'bin', process.platform === 'win32' ? 'image_metrics_ffi.exe' : 'image_metrics_ffi'); }
function runFfi(args: string[]): any {
  const exe = ffiPath();
  if (!fs.existsSync(exe)) throw new Error(`missing native image metrics bridge: ${exe}`);
  const proc = cp.spawnSync(exe, args, { encoding: 'utf-8' });
  if (proc.status !== 0) throw new Error(proc.stderr || `native command failed: ${args.join(' ')}`);
  return JSON.parse(proc.stdout);
}
export function backendVersion(): string { return fs.existsSync(ffiPath()) ? 'cpp-sparse-gaussian-ffi/0.2.0' : 'missing-cpp-ffi'; }
export function supportedExtensions(): string { return 'C++ sparse Gaussian update bridge; synthetic:// fixtures; raw byte files; PPM output'; }
export function analyzeImageToDir(req: AnalyzeImageRequest): NativeMetricResult {
  fs.mkdirSync(req.outDir, { recursive: true });
  const payload = runFfi(['analyze', req.imagePath]);
  fs.writeFileSync(path.join(req.outDir, 'report.json'), JSON.stringify(payload.result, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'feature_fixture.json'), JSON.stringify(payload, null, 2));
  fs.writeFileSync(path.join(req.outDir, 'summary.txt'), `backend: ${backendVersion()}\nsource: ${req.imagePath}\nscore: ${Number(payload.result.score).toFixed(6)}\n`);
  return payload.result as NativeMetricResult;
}
export function stochasticUpdateToDir(req: StochasticUpdateRequest): any {
  fs.mkdirSync(req.outDir, { recursive: true });
  return runFfi(['stochastic-update', req.imagePath, req.outDir, String(req.seed), String(req.trials), String(req.support), String(req.step)]);
}
