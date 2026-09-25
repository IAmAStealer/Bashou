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


HELP_HINT = ("Ask {tool} itself: `{tool} --help` (-h works for many tools, not all: `ls -h` means human sizes). "
             "The Usage line shows how to write it: [ ] is optional, ... means you can give several. "
             "Below, one line per option: short form (-x), long form (--xxx), what it does. "
             "Too long? `{tool} --help | less`, q quits.")


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
    skill: str = "bash"       # what it teaches (skills.SKILLS): only sent if you learn that
    help: str = ""            # what to look for in `tool --help`: beginners get that hint first
    fix: bool = False         # you fix a file (or run commands), then `verify`: Bashou checks the result
    works: Optional[Callable] = None    # () -> bool: something else this system must have (AddressSanitizer…)

    @property
    def tool(self):
        return self.tools[0] if self.tools else ""

    def task_text(self, meta):
        from ..i18n import _
        return fill(_(self.task), meta)

    def hint_list(self, meta):
        """The hints of this fight; beginners (meta["help_first"]) first learn to read --help."""
        from ..i18n import _
        hints = [fill(_(h), meta) for h in self.hints]
        if meta.get("help_first") and self.help:
            hints.insert(0, _(HELP_HINT).format(tool=self.tool) + " " + fill(_(self.help), meta))
        return hints

    def hint_text(self, i, meta):
        return self.hint_list(meta)[i]

    def used_by(self, analysis):
        return self.uses(analysis) if self.uses else bool(analysis.tools & set(self.tools))

    def check(self, work, meta, value):
        if self.verify:
            return self.verify(work, meta, value)
        return value.strip() == str(meta["answer"])

    def available(self):
        if self.distro and not set(self.distro) & family():
            return False
        from ..which import installed
        return all(installed(t) for t in (self.requires or [self.tool])) and (self.works is None or self.works())


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


from . import awk, basics, cicd, code, debug, find, grep, network, packages, pipe, ps, repos, rust, secrets, sed, security, sql, trials, uniq  # noqa: E402

ALL = basics.ALL + [grep.CHALLENGE, awk.CHALLENGE, find.CHALLENGE, uniq.CHALLENGE,
                    sed.CHALLENGE, ps.CHALLENGE, pipe.CHALLENGE] + code.ALL + debug.ALL + rust.ALL + packages.ALL + repos.ALL + cicd.ALL + sql.ALL + secrets.ALL + network.ALL   # fights
SECURITY = security.SECURITY        # `bashou security`, in order
TRIALS = trials.TRIALS + [cicd.INDENT_CHEST, sql.CHEST, secrets.CHEST, debug.CHEST, network.CHEST]   # locked chests in `bashou adventure`
BY_ID = {c.id: c for c in ALL + SECURITY + TRIALS}
