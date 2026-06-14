declare const require: any;
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

import { buildStatus, ensureManifestValid, readManifest } from '../src';
import { runCli } from '../src/cli';

const manifest = ensureManifestValid({
  format: 'LS_GIZMO_V1',
  name: 'metrics-lab',
  gadgets: {
    'image-metrics': {
      root: 'tools/milk_metrics',
      language: 'python',
      allowed_ops: ['read', 'write', 'mkdir', 'copy', 'run'],
      commands: {
        analyze: 'python -m milk_metrics.cli analyze {image} --out {out}',
      },
    },
    'text-metrics': {
      root: 'tools/text_metrics',
      language: 'typescript',
      allowed_ops: ['read', 'write', 'mkdir', 'copy', 'run'],
      commands: {
        analyze: 'node dist/src/cli.js analyze {file} --out {out}',
      },
    },
  },
});

const status = buildStatus(manifest);
assert.strictEqual(status.gadget_count, 2);
assert.deepStrictEqual(status.gadgets.map(g => g.name), ['image-metrics', 'text-metrics']);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gizmo-smoke-'));
const file = path.join(dir, 'empty.gizmo.json');
assert.strictEqual(runCli(['init', 'empty', '--out', file]), 0);
assert.strictEqual(readManifest(file).format, 'LS_GIZMO_V1');
assert.strictEqual(runCli(['validate', file]), 0);
assert.strictEqual(runCli(['status', file]), 0);
console.log('Gizmo smoke test passed');
