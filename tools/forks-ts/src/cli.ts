import { spawnSync } from 'node:child_process';

export interface InvocationPlan {
  corePath: string;
  coreArgs: string[];
  command: string;
  mutationScope: 'read-only';
}

export function usage(): string {
  return [
    'Usage:',
    '  forks-ts [--core-path <forks-core>] status [--gadget <gizmo> <gadget>]',
    '  forks-ts [--core-path <forks-core>] audit --gadget <gizmo> <gadget>',
    '',
    'This wrapper is intentionally thin. It validates operator-facing shape,',
    'then delegates deterministic filesystem, git, ledger, and audit mechanics',
    'to forks-core.'
  ].join('\n');
}

function requireGadgetArgs(command: string, rest: string[]): void {
  const gadgetIdx = rest.indexOf('--gadget');
  if (gadgetIdx === -1 || !rest[gadgetIdx + 1] || !rest[gadgetIdx + 2]) {
    throw new Error(`${command} requires --gadget <gizmo> <gadget>`);
  }
}

export function planInvocation(args: string[], envCorePath = process.env.FORKS_CORE ?? 'forks-core'): InvocationPlan {
  const rest = [...args];
  let corePath = envCorePath;
  if (rest[0] === '--core-path') {
    const configured = rest[1];
    if (!configured) throw new Error('missing value for --core-path');
    corePath = configured;
    rest.splice(0, 2);
  }
  const command = rest[0];
  if (!command) throw new Error('missing command');
  if (command !== 'status' && command !== 'audit') {
    throw new Error(`unsupported forks-ts command in read-only scaffold: ${command}`);
  }
  if (command === 'audit') requireGadgetArgs(command, rest);
  if (command === 'status' && rest.includes('--gadget')) requireGadgetArgs(command, rest);
  return { corePath, coreArgs: rest, command, mutationScope: 'read-only' };
}

export function runForksTs(args = process.argv.slice(2)): number {
  let plan: InvocationPlan;
  try {
    plan = planInvocation(args);
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    console.error(usage());
    return 1;
  }

  const result = spawnSync(plan.corePath, plan.coreArgs, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  if (result.error) {
    console.error(`failed to run forks-core at ${plan.corePath}: ${result.error.message}`);
    return 1;
  }
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  return result.status ?? 1;
}

if (require.main === module) {
  process.exit(runForksTs());
}
