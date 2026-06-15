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

export interface UnaryExpression {
  kind: 'UnaryExpression';
  operator: '!' | 'not';
  operand: Expression;
  span?: Span;
}

export interface BinaryExpression {
  kind: 'BinaryExpression';
  operator: string;
  left: Expression;
  right: Expression;
  span?: Span;
}

export interface IfExpression {
  kind: 'IfExpression';
  condition: Expression;
  thenBranch: Expression;
  elseBranch: Expression;
  span?: Span;
}

export interface LetExpression {
  kind: 'LetExpression';
  name: Identifier;
  value: Expression;
  body: Expression;
  span?: Span;
}

export type Expression =
  | Identifier
  | Literal
  | CallExpression
  | UnaryExpression
  | BinaryExpression
  | IfExpression
  | LetExpression;

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
  | 'void'
  | 'handle'
  | 'f64buf'
  | 'i32buf';

export interface ForeignSignature {
  params: ForeignPrimitiveType[];
  result: ForeignPrimitiveType;
}

export interface FunctionSignature {
  params: ForeignPrimitiveType[];
  result: ForeignPrimitiveType;
}

export interface FunctionDeclaration extends Statement {
  kind: 'FunctionDeclaration';
  name: Identifier;
  params: Identifier[];
  signature: FunctionSignature;
  body: Expression;
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
  | FunctionDeclaration
  | ForeignImport;
