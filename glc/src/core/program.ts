import { TopLevel } from './ast';

export interface Module {
  kind: 'Module';
  name: string;
  declarations: TopLevel[];
}

export interface Program {
  kind: 'Program';
  modules: Module[];
}
