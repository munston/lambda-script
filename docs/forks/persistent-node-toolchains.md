# Persistent Node and TypeScript toolchains

The repository uses package-local Node toolchains.

Do not rely on `set PATH=...`, `setx PATH=...`, or global `tsc`. Those are shell-environment state. The durable compiler is declared in each package's `package.json` and installed into that package's `node_modules`.

Use:

```bat
forks.bat ensure-node-toolchains --install
```

or:

```bat
python scripts\forks\ensure_node_toolchains.py --install
```

The script checks known package directories, installs missing local dependencies, and verifies TypeScript with the package-local compiler.

For `tools/gizmo`, the build script calls the package-local compiler directly:

```bat
node .\node_modules\typescript\bin\tsc -p tsconfig.json
```

This avoids the npm behaviour where `npm exec -- tsc` can prompt to install the unrelated deprecated `tsc` package when local `typescript` is absent.
