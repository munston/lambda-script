# Tarball spring

The tarball spring is for larger external edits where JSON patches are too bulky.

## Spring location

```text
spring/tarball/drop/
```

Only 0 or 1 tarballs should be present there.

## Archive location

```text
spring/tarball/archive/
```

After a tarball is absorbed successfully, it is moved to a timestamped archive filename.

## Work location

```text
spring/tarball/work/
```

Temporary extraction/work area.

## Accepted extensions

```text
.tar
.tar.gz
.tgz
.tar.bz2
.tbz2
.tar.xz
.txz
```

## Semantics

The tarball is an overlay:

```text
create missing files
overwrite existing files
do not delete absent files
```

## Safety rules

The absorber rejects:

```text
absolute paths
paths containing ..
.git paths
spring/tarball self-writes
symlinks and non-regular files
private-key-like filenames
multiple tarballs in the drop location
```

## Command

```sh
bash scripts/tarball_spring/absorb-and-ship.sh
```
