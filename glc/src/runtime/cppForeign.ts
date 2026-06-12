import { spawnSync } from 'child_process';

export type CppForeignValue = number | boolean | string | null;

export interface CppForeignRequest {
  symbol: string;
  args: CppForeignValue[];
}

export interface CppForeignRuntime {
  call(request: CppForeignRequest): CppForeignValue;
}

export class CppProcessRuntime implements CppForeignRuntime {
  constructor(private executable: string) {}

  call(request: CppForeignRequest): CppForeignValue {
    const result = spawnSync(this.executable, [JSON.stringify(request)], { encoding: 'utf8' });
    if (result.status !== 0) throw new Error(result.stderr || 'FFI call failed');
    const res = JSON.parse(result.stdout);
    if (!res.ok) throw new Error(res.error || 'FFI error');
    return res.value;
  }
}
