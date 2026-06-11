# Safe Git interface

This repository exposes only two top-level batch commands:

```bat
pull.bat
push.bat
```

All other batch files are internal implementation details under `scripts\`.

## Maintained targets

`git.config` lists the targets maintained by this interface.

Format:

```text
name|path|remote|branch|test-script
```

Current target:

```text
lambda-script|.|origin|main|scripts\targets\lambda-script\test.bat
```

## Pull

```bat
pull.bat
```

Equivalent internal Git subset:

```text
git status --short --branch
git fetch origin
git pull --ff-only origin main
git status --short --branch
```

A selected target may be pulled by name:

```bat
pull.bat lambda-script
```

## Push

```bat
push.bat "commit message"
```

Equivalent internal Git subset:

```text
git status --short --branch
git fetch origin
configured test script
git add -A
git diff --cached --quiet
git commit -m "commit message"
git push origin HEAD:main
```

A selected target may be pushed by name:

```bat
push.bat "commit message" lambda-script
```

## Excluded commands

The wrapper layer intentionally excludes:

```text
git reset --hard
git clean -fd
git rebase
git merge
git push --force
git commit --amend
git checkout -- file
```
