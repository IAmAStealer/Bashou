"""Is a command installed? Pets and hints only propose what this system has.

Remembered for 10 minutes: a lookup for a missing command walks the whole PATH, which is slow on WSL
(Windows folders under /mnt/c), and the pets ask often. A tool installed meanwhile shows up soon after.
"""

import functools
import shutil
import sys
import time
from pathlib import Path

from .i18n import _

TTL = 600
_seen = {}


def installed(name):
    now = time.monotonic()
    hit = _seen.get(name)
    if hit is None or now - hit[0] > TTL:
        hit = _seen[name] = (now, shutil.which(name) is not None)
    return hit[1]


installed.cache_clear = _seen.clear          # tests


def platform():
    """"macos" or "linux": the OS Bashou runs on, read each time (never saved at install). Fights follow it;
    what you learn follows `bashou config os` (skills.oses)."""
    return "macos" if sys.platform == "darwin" else "linux"


@functools.lru_cache(maxsize=None)
def os_family(path="/etc/os-release"):
    """{ID} plus ID_LIKE from os-release: {"ubuntu", "debian"}, {"rocky", "rhel", "centos", "fedora"}…"""
    try:
        text = Path(path).read_text()
    except OSError:
        return frozenset()
    found = set()
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key in ("ID", "ID_LIKE"):
            found |= set(value.strip().strip('"').split())
    return frozenset(found)


SYSTEMS = {"debian": {"debian"}, "rocky": {"rhel", "fedora", "centos"}}     # skill -> os-release ids


def system():
    """"debian", "rocky" (the Red Hat family) or None: whose packages this system has, named like
    the skill that teaches them. Package fights and Bashou's own apt/dnf repository follow it."""
    ids = os_family()
    return next((name for name, family in SYSTEMS.items() if family & ids), None)


# Packages that bring a tool: (Debian/Ubuntu, Red Hat family).
PACKAGES = {"rustc": ("rustc cargo", "rust cargo"), "gpg": ("gnupg", "gnupg2"), "pass": ("pass", "pass"),
            "sqlite3": ("sqlite3", "sqlite"), "python3": ("python3", "python3"), "gcc": ("gcc", "gcc"),
            "gdb": ("gdb", "gdb"), "git": ("git", "git"), "tcpdump": ("tcpdump", "tcpdump"),
            "openssl": ("openssl", "openssl"), "yamllint": ("yamllint", "yamllint")}


def install(tool):
    """How to install a tool here, with this system's package manager."""
    debian, redhat = PACKAGES[tool]
    if system() == "debian":
        return f"sudo apt install {debian}"
    if tool == "pass" and "rhel" in os_family():
        return "sudo dnf install epel-release && sudo dnf install pass"     # pass lives in EPEL on RHEL, Rocky, Alma
    if system() == "rocky":
        return f"sudo dnf install {redhat}"
    if tool == "rustc":
        return "curl -sSf https://sh.rustup.rs -o rustup.sh && less rustup.sh && sh rustup.sh"
    return _("your package manager (package {name})").format(name=debian)
