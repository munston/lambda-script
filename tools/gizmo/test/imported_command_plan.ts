declare const require: any;
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

import { buildImportedCommandPlan, ensureManifestValid } from '../src';
import { runCli } from '../src/cli';

const manifest = ensureManifestValid({
  format: 'LS_GIZMO_V1',
  name: 'metrics-import-command-test',
  gadgets: {
    'image-metrics': {
      root: 'tools/milk_metrics',
      commands: {
        analyze: 'python -m milk_metrics.cli analyze {image} --out {out}'
      }
    }
  },
  imports: {
    'lambdascript-core': {
      from_gizmo: 'lambdascript',
      from_gadget: 'core',
      mount: 'toolchains/lambdascript',
      mode: 'read-only',
      target_ref: 'origin/gadgets/lambdascript/core/main',
      allowed_commands: ['gizmo', 'forks', 'glc'],
      write_policy: 'deny'
    },
    'scratch-copy': {
      from_gizmo: 'metrics',
      from_gadget: 'text-metrics',
      mount: 'scratch/text-metrics',
      mode: 'copy',
      target_ref: 'origin/gadgets/metrics/text-metrics/main',
      allowed_commands: ['analyze']
    }
  }
});

const plan = buildImportedCommandPlan(manifest, 'lambdascript-core', 'gizmo');
assert.strictEqual(plan.format, 'LS_GIZMO_COMMAND_PLAN_V1');
assert.strictEqual(plan.gizmo, 'metrics-import-command-test');
assert.strictEqual(plan.scope, 'import');
assert.strictEqual(plan.name, 'lambdascript-core');
assert.strictEqual(plan.command, 'gizmo');
assert.strictEqual(plan.template, 'gizmo');
assert.strictEqual(plan.rendered, 'gizmo');
assert.deepStrictEqual(plan.args, {});
assert.strictEqual(plan.cwd, 'toolchains/lambdascript');
assert.strictEqual(plan.execute, false);
assert.deepStrictEqual(plan.missing_args, []);
assert.deepStrictEqual(plan.unused_args, []);
assert.strictEqual(plan.source, 'lambdascript/core');
assert.strictEqual(plan.mount, 'toolchains/lambdascript');
assert.strictEqual(plan.mode, 'read-only');
assert.strictEqual(plan.target_ref, 'origin/gadgets/lambdascript/core/main');
assert.strictEqual(plan.write_policy, 'deny');

const copyPlan = buildImportedCommandPlan(manifest, 'scratch-copy', 'analyze');
assert.strictEqual(copyPlan.write_policy, 'copy-on-write');
assert.strictEqual(copyPlan.mode, 'copy');

assert.throws(() => buildImportedCommandPlan(manifest, 'missing', 'gizmo'), /unknown import/);
assert.throws(() => buildImportedCommandPlan(manifest, 'lambdascript-core', 'unknown'), /does not allow command/);
assert.throws(() => buildImportedCommandPlan(manifest, 'lambdascript-core', 'bad&cmd'), /unsafe imported command name/);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gizmo-import-call-'));
const file = path.join(dir, 'manifest.gizmo.json');
fs.writeFileSync(file, JSON.stringify(manifest, null, 2) + '\n');

assert.strictEqual(runCli(['import-call', file, 'lambdascript-core', 'gizmo']), 0);
assert.strictEqual(runCli(['import-call', file, 'lambdascript-core', 'gizmo', '--exec=false']), 0);
assert.strictEqual(runCli(['import-call', file, 'lambdascript-core', 'gizmo', '--exec']), 1);
assert.strictEqual(runCli(['import-call', file, 'lambdascript-core', 'gizmo', '--arg', 'x=y']), 1);
assert.strictEqual(runCli(['import-call', file, 'lambdascript-core', 'unknown']), 1);

console.log('Gizmo imported command plan test passed');
