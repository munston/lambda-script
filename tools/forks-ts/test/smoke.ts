import assert from 'node:assert/strict';
import { planInvocation } from '../src/cli';

const status = planInvocation(['--core-path', 'C:/tools/forks-core.exe', 'status']);
assert.strictEqual(status.corePath, 'C:/tools/forks-core.exe');
assert.deepStrictEqual(status.coreArgs, ['status']);
assert.strictEqual(status.command, 'status');
assert.strictEqual(status.mutationScope, 'read-only');

const statusGadget = planInvocation(['status', '--gadget', 'lambdascript', 'core'], 'forks-core-test');
assert.strictEqual(statusGadget.corePath, 'forks-core-test');
assert.deepStrictEqual(statusGadget.coreArgs, ['status', '--gadget', 'lambdascript', 'core']);

const audit = planInvocation(['audit', '--gadget', 'lambdascript', 'core'], 'forks-core-test');
assert.strictEqual(audit.corePath, 'forks-core-test');
assert.deepStrictEqual(audit.coreArgs, ['audit', '--gadget', 'lambdascript', 'core']);
assert.strictEqual(audit.command, 'audit');
assert.strictEqual(audit.mutationScope, 'read-only');

assert.throws(
  () => planInvocation(['agent-land']),
  /unsupported forks-ts command in read-only scaffold: agent-land/,
  'read-only wrapper should reject mutating commands at this stage',
);

assert.throws(
  () => planInvocation(['audit', '--gadget', 'lambdascript']),
  /audit requires --gadget <gizmo> <gadget>/,
  'audit should require complete gadget identity',
);

assert.throws(
  () => planInvocation(['status', '--gadget', 'lambdascript']),
  /status requires --gadget <gizmo> <gadget>/,
  'status should reject incomplete optional gadget identity',
);

console.log('forks-ts read-only scaffold smoke passed');
