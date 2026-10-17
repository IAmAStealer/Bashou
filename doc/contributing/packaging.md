# Packages: the apt and dnf repositories

Each release is also published as a `.deb` and a `.rpm` in two signed repositories on GitHub Pages
(`https://iamastealer.github.io/Bashou/`). The page there gives users the setup lines.

- `tools/package.py build vX.Y.Z dist/` builds the packages: the code goes to `/usr/share/bashou` (the same
  tree as a clone, plus a `VERSION` file), `/usr/bin/bashou` runs its commands, and the install
  byte-compiles it. Nothing turns the pet on: each user runs `bashou on`, which adds one `source` line
  to their `~/.bashrc`. `bashou update` tells packaged installs to use apt or dnf.
- `tools/package.py repo dist/ site/ KEYID` makes the repositories: a flat apt repository (`Suites: ./`,
  signed `InRelease`) and a dnf repository (signed packages, signed `repomd.xml` for `repo_gpgcheck=1`).
- `.github/workflows/packages.yml` runs both after each release and force-pushes `site/` to the
  `gh-pages` branch. Only the newest version is kept.

## Homebrew (macOS, 0.10.0)

`tools/package.py build` also writes `bashou-X.Y.Z.tar.gz`: the same tree as the packages (with `VERSION`),
the same bytes each time. The packages job attaches it to the release (in the signed `SHA256SUMS`), then the
`tap` job writes `Formula/bashou.rb` (`tools/package.py formula`) with the tarball's sha256 and pushes it to
the tap, `IAmAStealer/homebrew-bashou`. Users run `brew install iamastealer/bashou/bashou` then `bashou on`.

brew keeps each version in `Cellar/bashou/VERSION/libexec` and deletes the old one after an upgrade, so the
`~/.zshrc` line and the loaders use `opt/bashou/libexec` (`bashou/brew.py`). The formula uses the Mac's own
python3 (`uses_from_macos "python"`: Homebrew needs Apple's command line tools, which bring it). The macOS
CI job installs the formula from a local tap and checks `brew test`, `bashou version` and `bashou on`.

The token: Settings > Developer settings > Fine-grained tokens, repository `IAmAStealer/homebrew-bashou` only,
Contents read and write. Save it as the Actions secret `TAP_TOKEN` of this repository. Without it, the tap
job warns and the formula stays as it was.

## One-time setup (owner)

1. Create a signing key with no passphrase (the GitHub secret is what protects it), on a trusted machine:

   ```bash
   export GNUPGHOME=$(mktemp -d)
   gpg --batch --passphrase '' --quick-gen-key 'Bashou packages <you@example.org>' ed25519 sign 3y
   gpg --armor --export-secret-keys > bashou-signing.asc
   ```

2. Repository Settings > Secrets and variables > Actions > New repository secret: `BASHOU_SIGNING_KEY`,
   the content of `bashou-signing.asc`. Then keep a backup of that file offline and delete it here,
   with `$GNUPGHOME`.
3. Actions > Packages > Run workflow with the current release (e.g. `v0.4.2`): it creates `gh-pages`.
4. Settings > Pages: Deploy from a branch, `gh-pages`, `/ (root)`.

The key expires after 3 years: before that, extend it (`gpg --quick-set-expire`) and update the secret.
Users download the new public key again (`bashou.asc`) — or it stops verifying.

## Test locally

Docker is enough: build and sign in `ubuntu:24.04` (like the CI runner, with `rpm createrepo-c apt-utils
gnupg file`), then install from the `site/` folder in `debian:trixie` (`URIs: file:/site/deb/`) and in
`rockylinux:9` (`baseurl=file:///site/rpm/`).
