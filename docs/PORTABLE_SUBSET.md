# Portable Subset (v0 + FFI)

## Current Syntax

```ls
module Name

foreign cpp add_i32 : i32 -> i32 -> i32 = "ls_add_i32"
answer = add_i32(40, 2)
```

**Supported:** Modules, declarations, literals, identifiers, calls, `foreign cpp` declarations.

**Not yet supported:** User functions, records, tagged unions, pattern matching.
