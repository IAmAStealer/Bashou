"""Is a command installed? Pets and hints only propose what this system has."""

import shutil
from functools import lru_cache


@lru_cache(maxsize=None)
def installed(name):
    return shutil.which(name) is not None
