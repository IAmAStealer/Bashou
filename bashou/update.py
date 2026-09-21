"""New versions: a daily `git fetch` of the install folder, and `bashou update` to pull them.

Installs are a git clone, so no HTTP code here and nothing about you is sent: git only asks
GitHub for new commits. The pet restarts itself once the new code is on disk.
"""

import subprocess
import time
from pathlib import Path

from . import state
from .i18n import _

ROOT = Path(__file__).resolve().parent.parent
DAY = 24 * 3600


def git(*args, timeout=20):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          timeout=timeout, stdin=subprocess.DEVNULL)


def behind():
    """Commits on GitHub not installed yet, or None when unknown (not a clone, offline…)."""
    try:
        if not (ROOT / ".git").exists() or git("fetch", "--quiet").returncode:
            return None
        out = git("rev-list", "--count", "HEAD..@{upstream}")
        return int(out.stdout) if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def due(now=None):
    """Claim today's check, so only one terminal a day does it (and never when turned off)."""
    now = now or time.time()
    with state.locked() as s:
        if state.setting(s, "updates") != "on" or now - s["update_checked"] < DAY:
            return False
        s["update_checked"] = now
        return True


def note(count):
    if not count:
        return None
    return "🆕 " + _("A new Bashou is out ({n} change(s)) → bashou update").format(n=count)


def check():
    """Fetch, remember the result for `bashou`, and return the bubble text (or None)."""
    count = behind()
    if count is None:
        return None
    with state.locked() as s:
        s["update_behind"] = count
    return note(count)


def run():
    """`bashou update`."""
    if not (ROOT / ".git").exists():
        print("  " + _("This copy of Bashou isn't a git clone, so it can't update itself."))
        return 1
    before = git("rev-parse", "HEAD").stdout.strip()
    try:
        out = git("pull", "--ff-only", "--quiet", timeout=120)
    except subprocess.TimeoutExpired:
        out = None
    if not out or out.returncode:
        print("  " + _("Update failed:") + " " + (out.stderr.strip() if out else "timeout"))
        return 1
    with state.locked() as s:
        s["update_behind"] = 0
    changes = git("log", "--oneline", "--no-merges", f"{before}..HEAD").stdout.strip()
    if not changes:
        print("  " + _("Bashou is already up to date."))
        return 0
    print("  " + _("Updated! What's new:"))
    for line in changes.splitlines()[:15]:
        print("    " + line.split(" ", 1)[1])
    print("  " + _("Your pets switch to the new version by themselves."))
    return 0
