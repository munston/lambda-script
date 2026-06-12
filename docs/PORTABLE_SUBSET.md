# Portable Subset (v0)

## Current Syntax

```ls
module Name

answer = 42
name = "lambda"
flag = true
copy = answer
```

**Supported:**
- `module Name`
- `name = <number>`
- `name = "text"`
- `name = true` / `name = false`
- `copy = name` (identifier reference)

**Not yet supported:**
- Function calls
- Function definitions
- Records
- Tagged unions
- Pattern matching

**Out of scope for v0:**
- Mutation, effects, classes, inheritance, async, exceptions
