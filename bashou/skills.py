"""What you want to learn (owner, 2026-09-23): a bit of everything, or the skills you tick.

Asked once before the starter (`bashou start`), changed any time with `bashou config skills`. Fights and the
adventure's paths only come from those skills; fights you already won still come back for review.
"""

from . import which
from .i18n import _


# skill -> what it covers, in the order of the list (the adventure's topics, world.TOPICS)
SKILLS = {
    "bash": "Bash: grep, sed, awk, find, pipes",
    "linux": "Linux: files, users, permissions, processes",
    "systemd": "systemd: services, timers, logs",
    "debian": "Debian and Ubuntu: apt, dpkg, repositories",
    "rocky": "Rocky and Red Hat: dnf, rpm, repositories",
    "python": "Python: small scripts to fix",
    "c": "C: compiling, memory, pointers",
    "rust": "Rust: variables, types, the compiler",
    "logic": "Logic: coding basics, for beginners",
    "cicd": "CI/CD: pipelines, secrets, runners",
    "sql": "SQL: databases with SQLite (SELECT, JOIN, UPDATE)",
    "network": "Network: IPv4, IPv6, DNS, TCP",
}
# Fights need a program or a system: without it, the skill still has its adventure questions.
NEEDS = {"python": "python3", "c": "gcc", "rust": "rustc", "sql": "sqlite3"}


def picked(s):
    """The skills you learn: every one, or those you ticked."""
    return list(SKILLS) if s.get("skills", "all") == "all" else [k for k in SKILLS if k in s["skills"]]


def wanted(s, skill):
    return s.get("skills", "all") == "all" or skill in s["skills"]


def note(skill):
    """Why this skill has no fights here, or ""."""
    if skill in NEEDS and not which.installed(NEEDS[skill]):
        return _("no {program} here: questions only").format(program=NEEDS[skill])
    if skill in which.SYSTEMS and skill != which.system():
        return _("another system: questions only")
    return ""
