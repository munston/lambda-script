import { Declaration } from './ast';

export interface Module {
  kind: 'Module';
  name: string;
  declarations: Declaration[];
}

export interface Program {
  kind: 'Program';
  modules: Module[];
  entry?: string;
}
