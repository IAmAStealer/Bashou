"""New versions: a daily `git fetch` of the install folder, and `bashou update` to install them.

Installs are a git clone, so no HTTP code here and nothing about you is sent: git only asks
GitHub for new release tags. The pet restarts itself once the new code is on disk.
A .deb or .rpm install has no .git but a VERSION file: apt or dnf update it, not Bashou (see
repo_setup.py, which also moves a git clone to those repositories if you want).
"""

import subprocess
import time
from pathlib import Path

from . import changelog, state
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


def packaged():
    """The version written in a .deb/.rpm install, or None for a git clone."""
    try:
        return None if (ROOT / ".git").exists() else (ROOT / "VERSION").read_text().strip() or None
    except OSError:
        return None


def version():
    """This install's version: its release tag, "v0.2.1-3-gabc1234" between releases, or None."""
    if packaged():
        return packaged()
    try:
        out = git("describe", "--tags", "--match", "v*.*.*")
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def releases():
    """Release tags, newest first (after a fetch)."""
    latest()
    return git("tag", "--list", "v*.*.*", "--sort=-v:refname").stdout.split()


def switch(tag):
    """Install exactly this release."""
    known = releases()
    if tag not in known:
        print("  " + _("No release {version}. Releases: {list}").format(version=tag, list=", ".join(known[:8]) or "-"))
        return 1
    if git("rev-parse", "HEAD").stdout == git("rev-parse", f"{tag}^{{commit}}").stdout:
        print("  " + _("Bashou {version} is already installed.").format(version=tag))
        return 0
    out = git("-c", "advice.detachedHead=false", "checkout", "--quiet", tag, timeout=60)
    if out.returncode:
        print("  " + _("Update failed:") + " " + out.stderr.strip())
        return 1
    with state.locked() as s:
        s["update_available"] = ""
        s["update_checked"] = 0              # an older release: the next terminal offers the newest again
    print("  " + _("Bashou {version} installed. Your pets switch to it by themselves.").format(version=tag))
    print("  " + _("Back to the newest: bashou update"))
    return 0


def run(version=None, packages=False):
    """`bashou update`, or `bashou update --version v0.2.0` for a given release (older ones too).
    A git clone on Debian or Red Hat is offered to move to the apt or dnf repository, once (or with --packages)."""
    import sys
    from . import repo_setup
    if packaged():
        return repo_setup.upgrade()
    if not (ROOT / ".git").exists():
        print("  " + _("This copy of Bashou isn't a git clone, so it can't update itself."))
        return 1
    if packages:
        return repo_setup.offer(ROOT / "bashou.bash")
    if version:
        return switch("v" + version.lstrip("v"))
    if sys.stdin.isatty() and repo_setup.system() and not state.load().get("packages_declined"):
        moved = repo_setup.offer(ROOT / "bashou.bash")
        if moved == 0:
            return 0
        if moved == 2:                                     # "no": don't ask again, update with git
            with state.locked() as s:
                s["packages_declined"] = True
        print()
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
    notes = changelog.notes(ROOT, tag)          # the release notes; commit subjects for old releases
    changes = changelog.items(notes) if notes else git("log", "--format=%s", "--no-merges", f"{before}..HEAD").stdout.splitlines()[:15]
    for line in changes:
        print("    " + line)
    print("  " + _("Your pets switch to the new version by themselves."))
    return 0
