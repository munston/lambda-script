# Tarball spring

The tarball spring is a chronological local intake device.

Location:

```text
spring/tarball/drop/
```

Rules:

```text
0 tarballs: nothing to absorb
1 tarball: absorb it
more than 1 tarball: refuse
```

The tarball is an overlay edit package. Files inside the tarball create or overwrite repository files. v1 does not delete absent files.

Run from MSYS2 UCRT64:

```sh
bash scripts/tarball_spring/absorb-and-ship.sh
```

The script performs:

```text
pull.bat
inspect exactly one tarball
reject unsafe paths
copy tarball files into the repo, overwriting existing files
archive the tarball chronologically
verify interface
push.bat with the tarball commit message
```

Optional manifest inside the tarball:

```json
{
  "format": "LS_TARBALL_SPRING_V1",
  "commit_message": "Absorb compiler update"
}
```
