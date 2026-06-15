declare const require: any;
const assert = require('assert');

import { buildProvisionPlan, buildStatus, ensureManifestValid, validateManifest } from '../src';

function requireDefined<T>(value: T | undefined, label: string): T {
  assert.notStrictEqual(value, undefined, label);
  return value as T;
}

const manifest = ensureManifestValid({
  format: 'LS_GIZMO_V1',
  name: 'metrics-import-boundary-test',
  gadgets: {
    'image-metrics': {
      root: 'tools/milk_metrics',
      language: 'python',
      allowed_ops: ['read', 'write', 'mkdir', 'copy', 'run'],
      target_ref: 'origin/gadgets/metrics/image-metrics/main',
      integration_branch: 'gadgets/metrics/image-metrics/main',
      agent_branch_template: 'gadget-agents/metrics/image-metrics/{agent}',
      owned_paths: ['tools/milk_metrics/'],
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

const status = buildStatus(manifest);
assert.strictEqual(status.import_count, 2);
assert.deepStrictEqual(status.imports.map(i => i.name), ['lambdascript-core', 'scratch-copy']);
assert.strictEqual(status.imports[0].from_gizmo, 'lambdascript');
assert.strictEqual(status.imports[0].from_gadget, 'core');
assert.strictEqual(status.imports[0].mount, 'toolchains/lambdascript');
assert.strictEqual(status.imports[0].mode, 'read-only');
assert.strictEqual(status.imports[0].target_ref, 'origin/gadgets/lambdascript/core/main');
assert.deepStrictEqual(status.imports[0].allowed_commands, ['forks', 'gizmo', 'glc']);
assert.strictEqual(status.imports[0].write_policy, 'deny');

const plan = buildProvisionPlan(manifest);
assert.strictEqual(plan.format, 'LS_GIZMO_PROVISION_PLAN_V1');
assert.strictEqual(plan.name, 'metrics-import-boundary-test');
assert.strictEqual(plan.import_count, 2);
assert.strictEqual(plan.command_count, 4);

const readOnlyImport = requireDefined(plan.imports.find(i => i.name === 'lambdascript-core'), 'expected lambdascript-core import in provision plan');
assert.strictEqual(readOnlyImport.source, 'lambdascript/core');
assert.strictEqual(readOnlyImport.mount, 'toolchains/lambdascript');
assert.strictEqual(readOnlyImport.mode, 'read-only');
assert.strictEqual(readOnlyImport.target_ref, 'origin/gadgets/lambdascript/core/main');
assert.deepStrictEqual(readOnlyImport.allowed_commands, ['forks', 'gizmo', 'glc']);
assert.strictEqual(readOnlyImport.write_policy, 'deny');
assert.strictEqual(readOnlyImport.mutable, false);

const copyImport = requireDefined(plan.imports.find(i => i.name === 'scratch-copy'), 'expected scratch-copy import in provision plan');
assert.strictEqual(copyImport.mode, 'copy');
assert.strictEqual(copyImport.write_policy, 'copy-on-write');
assert.strictEqual(copyImport.mutable, true);

const badWritePolicyIssues = validateManifest({
  format: 'LS_GIZMO_V1',
  name: 'bad-write-policy',
  gadgets: {
    core: {
      root: '.',
      commands: {
        noop: 'echo {value}'
      }
    }
  },
  imports: {
    bad: {
      from_gizmo: 'lambdascript',
      from_gadget: 'core',
      mount: 'toolchains/lambdascript',
      mode: 'read-only',
      write_policy: 'mutate'
    }
  }
});
assert(badWritePolicyIssues.some(i => i.path === 'imports.bad.write_policy'), 'expected invalid write_policy issue');

const badMountIssues = validateManifest({
  format: 'LS_GIZMO_V1',
  name: 'bad-mount',
  gadgets: {
    core: {
      root: '.',
      commands: {
        noop: 'echo {value}'
      }
    }
  },
  imports: {
    bad: {
      from_gizmo: 'lambdascript',
      from_gadget: 'core',
      mount: '../escape',
      mode: 'read-only',
      write_policy: 'deny'
    }
  }
});
assert(badMountIssues.some(i => i.path === 'imports.bad.mount'), 'expected invalid mount issue');

console.log('Gizmo provision-plan import boundary test passed');
