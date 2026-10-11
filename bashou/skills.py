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
    uses: tuple = ()            # (program, what it's for): the programs beyond the usual commands, shown
                                # when you pick your skills, so you know what to install and why


# In the order of the list (the adventure's topics, world.TOPICS). Debian and Rocky fights also need
# their system (which.SYSTEMS).
SKILLS = {
    "bash": Skill("Bash: grep, sed, awk, find, pipes", uses=(
        ("git", "the git fights: commits, branches and merge conflicts, in a real repository"),)),
    "linux": Skill("Linux: files, users, permissions, processes", uses=(
        ("gpg", "the key fights: lock a file with a passphrase, sign it, check a signature"),
        ("pass", "the password store fights: keep secrets out of your scripts"))),
    "systemd": Skill("systemd: services, timers, logs"),
    "debian": Skill("Debian and Ubuntu: apt, dpkg, repositories"),
    "rocky": Skill("Rocky and Red Hat: dnf, rpm, repositories"),
    "python": Skill("Python: small scripts to fix", needs="python3", uses=(
        ("python3", "runs the small scripts you fix: every Python fight needs it"),)),
    "c": Skill("C: compiling, memory, pointers", needs="gcc", uses=(
        ("gcc", "builds the C programs you fix: every C fight needs it"),
        ("gdb", "the debugger fights: gdb stops a program and shows the line where it crashed"))),
    "rust": Skill("Rust: variables, types, the compiler", needs="rustc", uses=(
        ("rustc", "builds the Rust programs you fix: every Rust fight needs it"),)),
    "logic": Skill("Logic: coding basics, for beginners"),
    "cicd": Skill("CI/CD: pipelines, secrets, runners", uses=(
        ("yamllint", "optional: `check` runs it on your pipeline files, as real projects do before a push"),)),
    "sql": Skill("SQL: databases with SQLite (SELECT, JOIN, UPDATE)", needs="sqlite3", uses=(
        ("sqlite3", "runs your SQL on a small database file: every SQL fight needs it"),)),
    "network": Skill("Network: IPv4, IPv6, DNS, TCP", uses=(
        ("tcpdump", "the packet fights: watch a TCP connection open, packet by packet"),)),
}


def picked(s):
    """The skills you learn: every one, or those you ticked."""
    return list(SKILLS) if s.get("skills", "all") == "all" else [k for k in SKILLS if k in s["skills"]]


def wanted(s, skill):
    return s.get("skills", "all") == "all" or skill in s["skills"]


OPTIONAL = {"yamllint"}          # nice to have: no fight waits for it


def programs(skill):
    """(program, what it's for, installed?) for each program the skill uses."""
    return [(program, _(why), which.installed(program)) for program, why in SKILLS[skill].uses]


def missing(skills):
    """The programs these skills use that this computer doesn't have, each once, in list order."""
    found = []
    for skill in skills:
        found += [program for program, _why, ok in programs(skill) if not ok and program not in found]
    return found


def note(skill):
    """Why this skill has no fights here, or ""."""
    needs = SKILLS[skill].needs
    if needs and not which.installed(needs):
        return _("no {program} here: questions only").format(program=needs)
    if skill in which.SYSTEMS and skill != which.system():
        return _("another system: questions only")
    return ""
