declare const require: any;
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const root = path.resolve(__dirname, '..');
const src = path.join(root, 'native', 'image_metrics_ffi.cpp');
const outDir = path.join(root, 'bin');
const exe = path.join(outDir, process.platform === 'win32' ? 'image_metrics_ffi.exe' : 'image_metrics_ffi');

function existsOnPath(name) {
  const pathEnv = process.env.PATH || '';
  const parts = pathEnv.split(path.delimiter);
  for (const dir of parts) {
    const full = path.join(dir, name);
    if (fs.existsSync(full)) return full;
  }
  return null;
}

function compiler() {
  return process.env.CXX || existsOnPath('g++') || existsOnPath('clang++') || existsOnPath('c++');
}

fs.mkdirSync(outDir, { recursive: true });
const cxx = compiler();
if (!cxx) {
  console.log('[image-metrics] no C++ compiler found; TypeScript will use portable byte backend');
  process.exit(0);
}

const args = [src, '-std=c++17', '-O2', '-o', exe];
console.log(`[image-metrics] ${cxx} ${args.join(' ')}`);
const proc = cp.spawnSync(cxx, args, { stdio: 'inherit', shell: process.platform === 'win32' });
if (proc.status !== 0) process.exit(proc.status || 1);
