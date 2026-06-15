declare const require: any;
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

import { buildWorkspacePlan, ensureManifestValid } from '../src';
import { runCli } from '../src/cli';

function requireDefined<T>(value: T | undefined, label: string): T {
  assert.notStrictEqual(value, undefined, label);
  return value as T;
}

const manifest = ensureManifestValid({
  format: 'LS_GIZMO_V1',
  name: 'workspace-test',
  gadgets: {
    core: {
      root: 'tools/gizmo',
      commands: {
        noop: 'echo {value}'
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
    'pinned-sdk': {
      from_gizmo: 'sdk',
      from_gadget: 'core',
      mount: 'toolchains/sdk',
      mode: 'pinned',
      target_ref: 'origin/gadgets/sdk/core/main',
      allowed_commands: ['sdk'],
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

const plan = buildWorkspacePlan(manifest, 'workspace-root');
assert.strictEqual(plan.format, 'LS_GIZMO_WORKSPACE_PLAN_V1');
assert.strictEqual(plan.name, 'workspace-test');
assert.strictEqual(plan.workspace_root, 'workspace-root');
assert.strictEqual(plan.mount_count, 3);

const core = requireDefined(plan.mounts.find(item => item.name === 'lambdascript-core'), 'expected lambdascript-core mount');
assert.strictEqual(core.source, 'lambdascript/core');
assert.strictEqual(core.mount, 'toolchains/lambdascript');
assert.strictEqual(core.workspace_path, 'workspace-root/toolchains/lambdascript');
assert.strictEqual(core.mode, 'read-only');
assert.strictEqual(core.write_policy, 'deny');
assert.strictEqual(core.mutable, false);
assert.strictEqual(core.planned_action, 'bind-readonly');
assert.deepStrictEqual(core.allowed_commands, ['forks', 'gizmo', 'glc']);

const pinned = requireDefined(plan.mounts.find(item => item.name === 'pinned-sdk'), 'expected pinned-sdk mount');
assert.strictEqual(pinned.planned_action, 'checkout-pinned');
assert.strictEqual(pinned.mutable, false);

const copy = requireDefined(plan.mounts.find(item => item.name === 'scratch-copy'), 'expected scratch-copy mount');
assert.strictEqual(copy.workspace_path, 'workspace-root/scratch/text-metrics');
assert.strictEqual(copy.write_policy, 'copy-on-write');
assert.strictEqual(copy.mutable, true);
assert.strictEqual(copy.planned_action, 'copy-on-write');

const dotRoot = buildWorkspacePlan(manifest);
assert.strictEqual(dotRoot.workspace_root, '.');
assert.strictEqual(requireDefined(dotRoot.mounts.find(item => item.name === 'lambdascript-core'), 'expected dot-root mount').workspace_path, 'toolchains/lambdascript');

assert.throws(() => buildWorkspacePlan(manifest, '../escape'), /unsafe workspace path|unsafe workspace root/);
assert.throws(() => buildWorkspacePlan(manifest, 'C:/escape'), /unsafe workspace root/);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gizmo-workspace-plan-'));
const manifestFile = path.join(dir, 'manifest.gizmo.json');
const outFile = path.join(dir, 'workspace-plan.json');
fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + '\n');

assert.strictEqual(runCli(['workspace-plan', manifestFile]), 0);
assert.strictEqual(runCli(['workspace-plan', manifestFile, '--root', 'workspace-root', '--out', outFile]), 0);
const written = JSON.parse(fs.readFileSync(outFile, 'utf8'));
assert.strictEqual(written.format, 'LS_GIZMO_WORKSPACE_PLAN_V1');
assert.strictEqual(written.workspace_root, 'workspace-root');
assert.strictEqual(written.mount_count, 3);

console.log('Gizmo workspace plan test passed');
