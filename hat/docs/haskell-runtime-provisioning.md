# Haskell runtime provisioning for agent kernels

This note records the route that made Haskell available in the current Debian agent kernel.

## Environment observed

```text
Debian GNU/Linux 13 (trixie)
node v22.16.0
npm 10.9.2
ghc absent initially
cabal absent initially
runghc absent initially
```

The npm route was investigated first. The useful-looking npm package delegates to GHCup and still tries to reach external hosts, so it is blocked when public DNS or external downloads are unavailable.

## Working route

Use the internal Artifactory Debian mirror and install the Debian packages.

Do not embed secret values in committed files. Use the existing environment variables supplied by the runtime:

```text
CAAS_ARTIFACTORY_BASE_URL
CAAS_ARTIFACTORY_READER_USERNAME
CAAS_ARTIFACTORY_READER_PASSWORD
```

The effective mirror path is:

```text
/artifactory/debian-public
```

The working apt source used only:

```text
trixie
trixie-updates
```

The `trixie-security` suite returned 404 through this mirror and should be omitted for this provisioning route.

## Command shape

```sh
base="https://${CAAS_ARTIFACTORY_READER_USERNAME}:${CAAS_ARTIFACTORY_READER_PASSWORD}@${CAAS_ARTIFACTORY_BASE_URL}/artifactory/debian-public"
cat > /etc/apt/sources.list.d/debian.sources <<EOF
Types: deb
URIs: $base
Suites: trixie trixie-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp
EOF
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ghc cabal-install
```

Observed installed versions:

```text
ghc 9.6.6
cabal-install 3.10.3.0
runghc 9.6.6
```

## Cabal configuration for offline boot-package builds

After installation, Cabal's default generated config points at `hackage.haskell.org`. That fails in this kernel when public DNS is unavailable.

For local projects that depend only on boot packages supplied with GHC, use a minimal no-repository Cabal config:

```text
remote-repo-cache: /home/oai/.cache/cabal/packages
remote-build-reporting: none
jobs: $ncpus
installdir: /home/oai/.local/bin
```

This allows simple local packages depending on `base`, `directory`, `filepath`, and `process` to build without trying to contact Hackage.

## Verification performed

A local `hat` test project was built with:

```sh
cabal run installation_script.hs
```

The generated installer then installed the `hat` executable into `hat/bin`, and running the executable printed:

```text
hat!
```

## Practical rule for future agents

When a fresh kernel lacks Haskell, try the Artifactory Debian mirror route first. Treat npm/GHCup as secondary because the npm wrapper still requires external downloads unless a suitable internal mirror is configured.
