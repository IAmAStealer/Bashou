#!/bin/sh
# Bashou on macOS (test version): installs or updates ~/.bashou at one release, then loads it from ~/.zshrc.
#
#   curl -fsSLO https://github.com/IAmAStealer/Bashou/releases/download/macos-v0.9.1/install-macos.sh
#   less install-macos.sh      # read it first: it only touches ~/.bashou and ~/.zshrc (and ~/.bashrc for a bash 4.4+)
#   sh install-macos.sh
#
# The tag doesn't look like vX.Y.Z on purpose: `bashou update` on Linux only offers those.
set -eu

TAG=macos-v0.9.1
REPO=https://github.com/IAmAStealer/Bashou.git
DIR="$HOME/.bashou"

say() { printf '  %s\n' "$*"; }

if [ "$(uname -s)" != Darwin ]; then
    say "This installer is for macOS. On Linux, see the README: apt, dnf or git."
    exit 1
fi

# git and python3 come with Apple's command line tools. Without them, /usr/bin/git only offers to install them.
if ! xcode-select -p >/dev/null 2>&1 || ! git --version >/dev/null 2>&1 || ! python3 --version >/dev/null 2>&1; then
    say "Bashou needs git and python3, which come with Apple's command line tools."
    say "A window opens to install them. When it's done, run this installer again."
    xcode-select --install 2>/dev/null || true
    exit 1
fi

if [ -d "$DIR/.git" ]; then
    say "Updating $DIR to $TAG"
    git -C "$DIR" fetch --quiet --tags --force "$REPO"
    git -C "$DIR" -c advice.detachedHead=false checkout --quiet "$TAG"
elif [ -e "$DIR" ]; then
    say "$DIR already exists and isn't a Bashou download. Move it away, then run this installer again."
    exit 1
else
    say "Downloading Bashou $TAG into $DIR"
    git -c advice.detachedHead=false clone --quiet --branch "$TAG" "$REPO" "$DIR"
fi

# The line in ~/.zshrc (and ~/.bashrc when a bash 4.4+ is installed), the same way `bashou on` adds it.
cd "$DIR"
BASHOU_SHELL=zsh python3 -m bashou setup
