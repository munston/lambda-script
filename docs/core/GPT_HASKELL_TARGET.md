# Local GPT LambdaScript target

Status: Ed implementation scaffold.

This target deliberately avoids `hmatrix` and other external Haskell numeric packages. The goal is to write GPT-style support code directly in LambdaScript's ordinary Haskell-like syntax, then require the existing LambdaScript emitters to produce both TypeScript and Haskell from the same source.

## Current compiler boundary

The current admitted LambdaScript surface supports primitive `i32`, `f64`, `bool`, and `string` values, top-level values, typed functions, calls, arithmetic and comparison operators, conditionals, lexical `let`, recursion, and C++ FFI declarations.

That means the first GPT implementation layer must be scalar and dependency-free. Full vectors, matrices, records, lists, tensor layouts, tokenizer tables, and model-weight loading remain later compiler work. They should be implemented inside LambdaScript rather than imported from `hmatrix`.

## First local GPT layer

The first local GPT fixture is:

```text
examples/gpt/gpt2_local_scalar.ls
```

It contains scalar kernels that a later vector/tensor layer can lift over arrays once LambdaScript admits structural types:

```text
max2
exp_approx
softmax2_left
softmax2_right
attention_scale
causal_mask
residual_add
gelu_cubic
rsqrt_step
rsqrt3
layer_norm2_left
linear2
```

These are not a complete GPT model. They are the dependency-free scalar substrate for the GPT implementation. The acceptance rule for this step is that the same LambdaScript source must parse, check, and emit both TypeScript and Haskell.

## Intended build direction

1. Keep scalar GPT kernels in LambdaScript.
2. Add arrays/lists to LambdaScript.
3. Lift scalar kernels to vector operations in LambdaScript.
4. Add matrix layout and row/column operations in LambdaScript.
5. Add token and position embedding lookup in LambdaScript.
6. Add attention, feed-forward, block, decoder, and generation code in LambdaScript.
7. Emit TypeScript and Haskell from the same LambdaScript source.
8. Avoid adding `hmatrix` as a required target dependency.
