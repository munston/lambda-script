declare const require: any;
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

import { buildProvisionPlan, buildStatus, ensureManifestValid, readManifest } from '../src';
import { runCli } from '../src/cli';

const manifest = ensureManifestValid({
  format: 'LS_GIZMO_V1',
  name: 'metrics-lab',
  gadgets: {
    'image-metrics': {
      root: 'tools/milk_metrics',
      language: 'python',
      allowed_ops: ['read', 'write', 'mkdir', 'copy', 'run'],
      target_ref: 'origin/gadgets/metrics/image-metrics/main',
      integration_branch: 'gadgets/metrics/image-metrics/main',
      agent_branch_template: 'gadget-agents/metrics/image-metrics/{agent}',
      owned_paths: ['tools/milk_metrics/'],
      verification_profiles: {
        quick: ['python -m py_compile tools/milk_metrics/milk_metrics/*.py'],
      },
      commands: {
        analyze: 'python -m milk_metrics.cli analyze {image} --out {out}',
      },
    },
    'text-metrics': {
      root: 'tools/text_metrics',
      language: 'typescript',
      allowed_ops: ['read', 'write', 'mkdir', 'copy', 'run'],
      target_ref: 'origin/gadgets/metrics/text-metrics/main',
      integration_branch: 'gadgets/metrics/text-metrics/main',
      agent_branch_template: 'gadget-agents/metrics/text-metrics/{agent}',
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
  connections: [
    {
      from: 'text-metrics',
      to: 'image-metrics',
      via: 'declared-artifacts',
      allowed_reads: ['report.json'],
      allowed_commands: ['analyze'],
    },
  ],
});

const status = buildStatus(manifest);
assert.strictEqual(status.gadget_count, 2);
assert.strictEqual(status.import_count, 1);
assert.strictEqual(status.connection_count, 1);
assert.deepStrictEqual(status.gadgets.map(g => g.name), ['image-metrics', 'text-metrics']);
assert.strictEqual(status.gadgets[0].target_ref, 'origin/gadgets/metrics/image-metrics/main');
assert.strictEqual(status.gadgets[0].agent_branch_template, 'gadget-agents/metrics/image-metrics/{agent}');
assert.deepStrictEqual(status.imports.map(i => i.name), ['lambdascript-core']);
assert.strictEqual(status.imports[0].write_policy, 'deny');

const plan = buildProvisionPlan(manifest);
assert.strictEqual(plan.format, 'LS_GIZMO_PROVISION_PLAN_V1');
assert.strictEqual(plan.import_count, 1);
assert.strictEqual(plan.command_count, 3);
assert.strictEqual(plan.imports[0].source, 'lambdascript/core');
assert.strictEqual(plan.imports[0].mutable, false);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gizmo-smoke-'));
const file = path.join(dir, 'empty.gizmo.json');
const full = path.join(dir, 'full.gizmo.json');
const planFile = path.join(dir, 'provision-plan.json');
assert.strictEqual(runCli(['init', 'empty', '--out', file]), 0);
assert.strictEqual(readManifest(file).format, 'LS_GIZMO_V1');
assert.strictEqual(runCli(['validate', file]), 0);
assert.strictEqual(runCli(['status', file]), 0);
fs.writeFileSync(full, JSON.stringify(manifest, null, 2) + '\n');
assert.strictEqual(runCli(['validate', full]), 0);
assert.strictEqual(runCli(['status', full]), 0);
assert.strictEqual(runCli(['branches', full]), 0);
assert.strictEqual(runCli(['provision-plan', full]), 0);
assert.strictEqual(runCli(['provision-plan', full, '--out', planFile]), 0);
assert.strictEqual(JSON.parse(fs.readFileSync(planFile, 'utf8')).format, 'LS_GIZMO_PROVISION_PLAN_V1');
console.log('Gizmo smoke test passed');
