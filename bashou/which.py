"""Is a command installed? Pets and hints only propose what this system has.

Remembered for 10 minutes: a lookup for a missing command walks the whole PATH, which is slow on WSL
(Windows folders under /mnt/c), and the pets ask often. A tool installed meanwhile shows up soon after.
"""

import shutil
import time

TTL = 600
_seen = {}


def installed(name):
    now = time.monotonic()
    hit = _seen.get(name)
    if hit is None or now - hit[0] > TTL:
        hit = _seen[name] = (now, shutil.which(name) is not None)
    return hit[1]


installed.cache_clear = _seen.clear          # tests
