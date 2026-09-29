"""Is a command installed? Pets and hints only propose what this system has.

Remembered for 10 minutes: a lookup for a missing command walks the whole PATH, which is slow on WSL
(Windows folders under /mnt/c), and the pets ask often. A tool installed meanwhile shows up soon after.
"""

import functools
import shutil
import time
from pathlib import Path

TTL = 600
_seen = {}


def installed(name):
    now = time.monotonic()
    hit = _seen.get(name)
    if hit is None or now - hit[0] > TTL:
        hit = _seen[name] = (now, shutil.which(name) is not None)
    return hit[1]


installed.cache_clear = _seen.clear          # tests


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
