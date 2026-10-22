#!/bin/sh
# Bashou on macOS (test version): installs or updates ~/.bashou at one release, then loads it from ~/.zshrc.
#
#   curl -fsSLO https://github.com/IAmAStealer/Bashou/releases/download/macos-v0.9.1/install-macos.sh
#   less install-macos.sh      # read it first: it only touches ~/.bashou and ~/.zshrc (and ~/.bashrc for a bash 4.4+)
#   sh install-macos.sh
#
# The tag doesn't look like vX.Y.Z on purpose: `bashou update` on Linux only offers those.
set -u          # each step that can fail is checked below: set -e would miss some (bash-style.md, S4)

tag=macos-v0.9.1
repo=https://github.com/IAmAStealer/Bashou.git
dir="$HOME/.bashou"

say() { printf '  %s\n' "$@"; }
die() { printf '  %s\n' "$@" >&2; exit 1; }

[ "$(uname -s)" = Darwin ] || die "This installer is for macOS. On Linux, see the README: apt, dnf or git."

# git and python3 come with Apple's command line tools. Without them, /usr/bin/git only offers to install them.
if ! xcode-select -p >/dev/null 2>&1 || ! git --version >/dev/null 2>&1 || ! python3 --version >/dev/null 2>&1; then
    xcode-select --install 2>/dev/null || true
    die "Bashou needs git and python3, which come with Apple's command line tools." \
        "A window opens to install them. When it's done, run this installer again."
fi

if [ -d "$dir/.git" ]; then
    say "Updating $dir to $tag"
    git -C "$dir" fetch --quiet --tags --force "$repo" || die "Could not download $tag."
    git -C "$dir" -c advice.detachedHead=false checkout --quiet "$tag" || die "Could not switch to $tag."
elif [ -e "$dir" ]; then
    die "$dir already exists and isn't a Bashou download. Move it away, then run this installer again."
else
    say "Downloading Bashou $tag into $dir"
    git -c advice.detachedHead=false clone --quiet --branch "$tag" "$repo" "$dir" || die "Could not download $tag."
fi

# The line in ~/.zshrc (and ~/.bashrc when a bash 4.4+ is installed), the same way `bashou on` adds it.
cd "$dir" || die "Could not enter $dir."
BASHOU_SHELL=zsh python3 -m bashou setup || die "The setup failed: see the message above."
