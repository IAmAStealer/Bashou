"""Challenge bank for the arena.

Each challenge fills the arena folder with random data in `setup` and returns the
task text plus what `verify` needs (stored as JSON in the arena's meta file).
"""

import functools
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


def fill(text, meta):
    """Put meta["args"] into {placeholders}, leaving other braces alone (awk '{print $1}')."""
    for key, value in meta.get("args", {}).items():
        text = text.replace("{" + key + "}", str(value))
    return text


@dataclass
class Challenge:
    id: str
    pet: str                  # pet unlocked by winning
    tools: tuple              # the first is the one named; any of them counts
    threat: str               # name of the attacking threat
    task: str                 # what to do, with {placeholders} filled from meta["args"]
    hints: list
    setup: Callable           # (work_dir, rng) -> meta dict with "args" (and usually "answer")
    verify: Optional[Callable] = None   # (work_dir, meta, value) -> bool; default: value == answer
    cleanup: Optional[Callable] = None  # (meta) -> None
    uses: Optional[Callable] = None     # (analysis) -> bool: what must be used; default: one of `tools`
    requires: list = field(default_factory=list)   # executables needed on this system
    level: int = 1            # 1 easy, 2 medium, 3 hard
    kind: str = "fight"       # "fight": sent as a threat; "security": picked in `bashou security`
    after: tuple = ()         # fights to beat before this one comes (beginners first)
    distro: tuple = ()        # only on these families (os-release ID or ID_LIKE), e.g. ("debian",)

    @property
    def tool(self):
        return self.tools[0] if self.tools else ""

    def task_text(self, meta):
        from ..i18n import _
        return fill(_(self.task), meta)

    def hint_text(self, i, meta):
        from ..i18n import _
        return fill(_(self.hints[i]), meta)

    def used_by(self, analysis):
        return self.uses(analysis) if self.uses else bool(analysis.tools & set(self.tools))

    def check(self, work, meta, value):
        if self.verify:
            return self.verify(work, meta, value)
        return value.strip() == str(meta["answer"])

    def available(self):
        if self.distro and not set(self.distro) & family():
            return False
        return all(shutil.which(t) for t in (self.requires or [self.tool]))


@functools.lru_cache(maxsize=None)
def family(path="/etc/os-release"):
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


from . import awk, basics, code, find, grep, packages, pipe, ps, repos, rust, sed, security, trials, uniq  # noqa: E402

ALL = basics.ALL + [grep.CHALLENGE, awk.CHALLENGE, find.CHALLENGE, uniq.CHALLENGE,
                    sed.CHALLENGE, ps.CHALLENGE, pipe.CHALLENGE] + code.ALL + rust.ALL + packages.ALL + repos.ALL   # fights
SECURITY = security.SECURITY        # `bashou security`, in order
TRIALS = trials.TRIALS              # locked chests in `bashou adventure`
BY_ID = {c.id: c for c in ALL + SECURITY + TRIALS}
