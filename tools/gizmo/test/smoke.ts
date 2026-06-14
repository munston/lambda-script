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
      target_ref: 'origin/gadgets/metrics/image-metrics/main',
      integration_branch: 'gadgets/metrics/image-metrics/main',
      agent_branch_template: 'agents/{agent}/gadgets/metrics/image-metrics',
      owned_paths: ['tools/milk_metrics/'],
      verification_profiles: {
        quick: ['python -m py_compile tools/milk_metrics/milk_metrics/*.py'],
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
  imports: {
    'lambdascript-core': {
      from_gizmo: 'lambdascript',
      from_gadget: 'core',
      mount: 'toolchains/lambdascript',
      mode: 'read-only',
      target_ref: 'origin/gadgets/lambdascript/core/main',
      allowed_commands: ['forks', 'glc', 'gizmo'],
      write_policy: 'deny',
    },
  },
});

const status = buildStatus(manifest);
assert.strictEqual(status.gadget_count, 2);
assert.strictEqual(status.import_count, 1);
assert.deepStrictEqual(status.gadgets.map(g => g.name), ['image-metrics', 'text-metrics']);
assert.strictEqual(status.gadgets[0].target_ref, 'origin/gadgets/metrics/image-metrics/main');

for (const example of ['metrics-lab.gizmo.json', 'lambdascript.gizmo.json', 'metrics.gizmo.json', 'merlin.gizmo.json']) {
  const filePath = path.join(__dirname, '..', '..', '..', '..', 'examples', 'gizmos', example);
  if (fs.existsSync(filePath)) {
    const loaded = ensureManifestValid(readManifest(filePath));
    assert.strictEqual(buildStatus(loaded).format, 'LS_GIZMO_V1');
  }
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gizmo-smoke-'));
const file = path.join(dir, 'empty.gizmo.json');
assert.strictEqual(runCli(['init', 'empty', '--out', file]), 0);
assert.strictEqual(readManifest(file).format, 'LS_GIZMO_V1');
assert.strictEqual(runCli(['validate', file]), 0);
assert.strictEqual(runCli(['status', file]), 0);
console.log('Gizmo smoke test passed');
