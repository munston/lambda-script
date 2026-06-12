# Installation

## Prerequisites

- Node.js + npm
- git
- (Optional) g++ for the C++ FFI demo

## First Time Setup

From the repository root, run:

```bat
install.bat
```

## Verification

```bat
verify.bat
```

## C++ FFI Demo (Optional)

```bat
native\cppffi\build-demo.bat
native\cppffi\verify-demo.bat
```

## Notes

- TypeScript is installed locally inside `glc/node_modules`.
- Do **not** install TypeScript globally unless you know what you are doing.
- All build and test commands are defined in `glc/package.json`.
