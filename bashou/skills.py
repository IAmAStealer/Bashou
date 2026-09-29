"""What you want to learn (owner, 2026-09-23): a bit of everything, or the skills you tick.

Asked once before the starter (`bashou start`), changed any time with `bashou config skills`. Fights and the
adventure's paths only come from those skills; fights you already won still come back for review.
"""

from dataclasses import dataclass

from . import which
from .i18n import _


@dataclass(frozen=True)
class Skill:
    text: str                   # what it covers, as the list shows it ("Bash: grep, sed, awk, find, pipes")
    needs: str = ""             # the program its fights need; without it, the skill has questions only


# In the order of the list (the adventure's topics, world.TOPICS). Debian and Rocky fights also need
# their system (which.SYSTEMS).
SKILLS = {
    "bash": Skill("Bash: grep, sed, awk, find, pipes"),
    "linux": Skill("Linux: files, users, permissions, processes"),
    "systemd": Skill("systemd: services, timers, logs"),
    "debian": Skill("Debian and Ubuntu: apt, dpkg, repositories"),
    "rocky": Skill("Rocky and Red Hat: dnf, rpm, repositories"),
    "python": Skill("Python: small scripts to fix", needs="python3"),
    "c": Skill("C: compiling, memory, pointers", needs="gcc"),
    "rust": Skill("Rust: variables, types, the compiler", needs="rustc"),
    "logic": Skill("Logic: coding basics, for beginners"),
    "cicd": Skill("CI/CD: pipelines, secrets, runners"),
    "sql": Skill("SQL: databases with SQLite (SELECT, JOIN, UPDATE)", needs="sqlite3"),
    "network": Skill("Network: IPv4, IPv6, DNS, TCP"),
}


def picked(s):
    """The skills you learn: every one, or those you ticked."""
    return list(SKILLS) if s.get("skills", "all") == "all" else [k for k in SKILLS if k in s["skills"]]


def wanted(s, skill):
    return s.get("skills", "all") == "all" or skill in s["skills"]


def note(skill):
    """Why this skill has no fights here, or ""."""
    needs = SKILLS[skill].needs
    if needs and not which.installed(needs):
        return _("no {program} here: questions only").format(program=needs)
    if skill in which.SYSTEMS and skill != which.system():
        return _("another system: questions only")
    return ""
