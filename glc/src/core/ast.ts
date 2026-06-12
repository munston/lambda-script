export interface Span {
  file: string;
  start: number;
  end: number;
}

export interface Identifier {
  kind: 'Identifier';
  name: string;
  span?: Span;
}

export interface Literal {
  kind: 'Literal';
  value: string | number | boolean;
  span?: Span;
}

export interface CallExpression {
  kind: 'CallExpression';
  callee: Identifier;
  arguments: Expression[];
  span?: Span;
}

export type Expression =
  | Identifier
  | Literal
  | CallExpression;

export interface Statement {
  kind: string;
  span?: Span;
}

export interface Declaration extends Statement {
  kind: 'Declaration';
  name: Identifier;
  value: Expression;
}

export type ForeignTarget = 'cpp';

export type ForeignPrimitiveType =
  | 'i32'
  | 'f64'
  | 'bool'
  | 'string'
  | 'void';

export interface ForeignSignature {
  params: ForeignPrimitiveType[];
  result: ForeignPrimitiveType;
}

export interface ForeignImport extends Statement {
  kind: 'ForeignImport';
  target: ForeignTarget;
  name: Identifier;
  symbol: string;
  signature: ForeignSignature;
}

export type TopLevel =
  | Declaration
  | ForeignImport;
