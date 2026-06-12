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

export type Expression =
  | Identifier
  | Literal;

export interface Statement {
  kind: string;
  span?: Span;
}

export interface Declaration extends Statement {
  kind: 'Declaration';
  name: Identifier;
  value: Expression;
}
