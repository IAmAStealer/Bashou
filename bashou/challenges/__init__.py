"""Challenge bank for the arena.

Each challenge fills the arena folder with random data in `setup` and returns the
task text plus what `verify` needs (stored as JSON in the arena's meta file).
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..i18n import _
from .. import which


def fill(text, meta):
    """Put meta["args"] into {placeholders}, leaving other braces alone (awk '{print $1}')."""
    for key, value in meta.get("args", {}).items():
        text = text.replace("{" + key + "}", str(value))
    return text


def with_editor(meta, editor):
    """{editor} and {save_keys} in hints: the editor the player picked (`bashou config editor`)."""
    keys = {"nano": _("Ctrl+O then Enter to save, Ctrl+X to quit"),
            "vi": _("i to type, Esc when done, then :wq and Enter to save and quit")}
    meta.setdefault("args", {}).update(editor=editor, save_keys=keys.get(editor, keys["nano"]))
    return meta


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
    kind: str = "fight"       # "fight": sent as a threat; "security": picked in `bashou arena security`
    after: tuple = ()         # fights to beat before this one comes (beginners first)
    skill: str = "bash"       # what it teaches (skills.SKILLS): only sent if you learn that; debian/rocky: only there
    help: str = ""            # what to look for in `tool --help`: beginners get that hint first
    fix: bool = False         # you fix a file (or run commands), then `verify`: Bashou checks the result
    works: Optional[Callable] = None    # () -> bool: something else this system must have (AddressSanitizer…)
    why: Optional[Callable] = None      # (work_dir) -> str or None: what's wrong, said when `verify` fails
    file: str = ""            # the file you fix, when Bashou can read it for you before verify (`check`)
    zsh: str = ""             # what zsh does differently here: the last hint of zsh players (meta["shell"])
    needs: str = ""           # what hurts it when that's more than one of `tools` (a loop, a pipeline…)
    os: str = ""              # "linux": only on Linux (it needs ip, ss, /proc…); fights follow the machine itself

    @property
    def tool(self):
        return self.tools[0] if self.tools else ""

    def task_text(self, meta):
        return fill(_(self.task), meta)

    def hint_list(self, meta):
        """The hints of this fight; beginners (meta["help_first"]) first learn to read --help."""
        hints = [fill(_(h), meta) for h in self.hints]
        if meta.get("help_first") and self.help:
            hints.insert(0, _(HELP_HINT).format(tool=self.tool) + " " + fill(_(self.help), meta))
        if meta.get("shell") == "zsh" and self.zsh:
            hints.append(fill(_(self.zsh), meta))
        if meta.get("platform") == "macos" and "sed -i" in " ".join([self.task] + self.hints):
            hints.append(_("On macOS, sed -i wants a word for a backup copy right after it: give it an empty one, "
                           "sed -i '' 's/old/new/' file. Without it, macOS's sed takes your s/old/new/ for that "
                           "word and then can't read the rest."))
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
        if self.os and self.os != which.platform():
            return False
        if self.skill in which.SYSTEMS and self.skill != which.system():
            return False
        return all(which.installed(t) for t in (self.requires or [self.tool])) and (self.works is None or self.works())


from . import awk, basics, cicd, code, debug, everyday, find, gitfights, grep, logic, network, packages, pipe, ps, repos, rust, scripting, secrets, sed, security, sql, system, trials, uniq  # noqa: E402

MODULES = (basics, everyday, scripting, system, gitfights, grep, awk, find, uniq, sed, ps, pipe, code, debug, rust, packages, repos, cicd, sql, secrets, logic,
           network, trials)
ALL = [c for m in MODULES for c in getattr(m, "ALL", ())]            # fights
SECURITY = security.SECURITY        # `bashou arena security`, in order
TRIALS = [c for m in MODULES for c in getattr(m, "CHESTS", ())]      # locked chests in `bashou adventure`
BY_ID = {c.id: c for c in ALL + SECURITY + TRIALS}
