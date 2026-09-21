"""New versions: a daily `git fetch` of the install folder, and `bashou update` to install them.

Installs are a git clone, so no HTTP code here and nothing about you is sent: git only asks
GitHub for new release tags. The pet restarts itself once the new code is on disk.
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


def latest():
    """Newest release tag (vX.Y.Z) after a fetch, or None (not a clone, offline, no release yet).

    Releases are tagged by the Release workflow only after every CI check passed, so pets never
    offer a random commit from main.
    """
    try:
        if not (ROOT / ".git").exists() or git("fetch", "--quiet", "--tags", "--force").returncode:
            return None
        tags = git("tag", "--list", "v*.*.*", "--sort=-v:refname").stdout.split()
        return tags[0] if tags else None
    except (OSError, subprocess.SubprocessError):
        return None


def installed(tag):
    """True if this install already contains `tag`."""
    return git("merge-base", "--is-ancestor", tag, "HEAD").returncode == 0


def available():
    """The release to install, or None."""
    tag = latest()
    try:
        return tag if tag and not installed(tag) else None
    except (OSError, subprocess.SubprocessError):
        return None


def due(now=None):
    """Claim today's check, so only one terminal a day does it (and never when turned off)."""
    now = now or time.time()
    with state.locked() as s:
        if state.setting(s, "updates") != "on" or now - s["update_checked"] < DAY:
            return False
        s["update_checked"] = now
        return True


def note(tag):
    return "🆕 " + _("Bashou {version} is out → bashou update").format(version=tag) if tag else None


def check():
    """Fetch, remember the result for `bashou`, and return the bubble text (or None)."""
    tag = available()
    with state.locked() as s:
        s["update_available"] = tag or ""
    return note(tag)


def run():
    """`bashou update`."""
    if not (ROOT / ".git").exists():
        print("  " + _("This copy of Bashou isn't a git clone, so it can't update itself."))
        return 1
    tag = available()
    with state.locked() as s:
        s["update_available"] = ""
    if not tag:
        print("  " + _("Bashou is already up to date."))
        return 0
    before = git("rev-parse", "HEAD").stdout.strip()
    out = git("-c", "advice.detachedHead=false", "checkout", "--quiet", tag, timeout=60)
    if out.returncode:
        print("  " + _("Update failed:") + " " + out.stderr.strip())
        return 1
    print("  " + _("Updated to {version}! What's new:").format(version=tag))
    changes = git("log", "--format=%s", "--no-merges", f"{before}..HEAD").stdout.splitlines()
    for line in changes[:15]:
        print("    " + line)
    print("  " + _("Your pets switch to the new version by themselves."))
    return 0
