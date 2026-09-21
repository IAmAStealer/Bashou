"""Challenge bank for the arena.

Each challenge fills the arena folder with random data in `setup` and returns the
task text plus what `verify` needs (stored as JSON in the arena's meta file).
"""

import shutil
from dataclasses import dataclass, field
from typing import Callable, Optional


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

    @property
    def tool(self):
        return self.tools[0]

    def task_text(self, meta):
        from ..i18n import _
        return _(self.task).format(**meta.get("args", {}))

    def used_by(self, analysis):
        return self.uses(analysis) if self.uses else bool(analysis.tools & set(self.tools))

    def check(self, work, meta, value):
        if self.verify:
            return self.verify(work, meta, value)
        return value.strip() == str(meta["answer"])

    def available(self):
        return all(shutil.which(t) for t in (self.requires or [self.tool]))


from . import find, grep, awk, pipe, ps, sed, uniq  # noqa: E402

ALL = [grep.CHALLENGE, awk.CHALLENGE, find.CHALLENGE, uniq.CHALLENGE, sed.CHALLENGE, ps.CHALLENGE,
       pipe.CHALLENGE]
BY_ID = {c.id: c for c in ALL}
