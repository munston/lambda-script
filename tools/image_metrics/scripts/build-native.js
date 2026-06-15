const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const root = path.resolve(__dirname, '..');
const src = path.join(root, 'native', 'image_metrics_ffi.cpp');
const outDir = path.join(root, 'bin');
const exe = path.join(outDir, process.platform === 'win32' ? 'image_metrics_ffi.exe' : 'image_metrics_ffi');

function existsOnPath(name) {
  for (const dir of (process.env.PATH || '').split(path.delimiter)) {
    const full = path.join(dir, name);
    if (fs.existsSync(full)) return full;
    if (process.platform === 'win32' && fs.existsSync(full + '.exe')) return full + '.exe';
  }
  return null;
}

fs.mkdirSync(outDir, { recursive: true });
const cxx = process.env.CXX || existsOnPath('g++') || existsOnPath('clang++') || existsOnPath('c++');
if (!cxx) {
  console.log('[image-metrics] no C++ compiler found; TypeScript fallback remains available');
  process.exit(0);
}
const args = [src, '-std=c++17', '-O2', '-o', exe];
console.log(`[image-metrics] ${cxx} ${args.join(' ')}`);
const proc = cp.spawnSync(cxx, args, { cwd: root, stdio: 'inherit' });
if (proc.status !== 0) process.exit(proc.status || 1);
