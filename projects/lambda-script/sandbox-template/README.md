# Sandbox folder template

Copy this folder outside the implementation tree and edit the placeholders. The local agent should work from the copied sandbox directory and use only `cabal run sandbox -- ...`.

Files to create in the copied sandbox:

```text
cabal.project
sandbox.json
```

Example commands after configuration:

```bat
cabal run sandbox -- onepush
cabal run sandbox -- onepush --ship
cabal run sandbox -- land "C:\Users\guyas\Downloads\patch.json"
```
