"""Bashou from Homebrew (0.10.0): `brew install iamastealer/bashou/bashou` (the tap repository
IAmAStealer/homebrew-bashou, its formula written by tools/package.py at each release).

brew puts each version in its own folder, Cellar/bashou/VERSION/libexec, and removes the old one after an
upgrade; opt/bashou always points at the current one. Paths kept for later (the ~/.zshrc line) use opt/.
"""

from pathlib import Path

UPGRADE = "brew upgrade bashou"


def stable(path):
    """`path` with PREFIX/Cellar/bashou/VERSION/libexec turned into PREFIX/opt/bashou/libexec."""
    parts = Path(path).parts
    for i in range(1, len(parts) - 3):
        if parts[i] == "Cellar" and parts[i + 1] == "bashou" and parts[i + 3] == "libexec":
            return Path(*parts[:i], "opt", "bashou", *parts[i + 3:])
    return Path(path)


def installed(root):
    """Is `root` (the folder with launch.py) a Homebrew install?"""
    root = stable(root)
    return root.parts[-3:] == ("opt", "bashou", "libexec")
