"""Move a git install to Bashou's apt or dnf repository (owner, 2026-09-24): updates then come with the rest
of the system, signed.

Nothing happens behind your back: every command is shown first, you say yes once, then each one runs in
front of you (sudo asks for your password itself) and the first failure stops everything. The repository
files are written from here and put in place with `sudo install`; only the key is downloaded, with curl or
wget, like the packages page says. Your progress is kept: it lives in ~/.local/share/bashou either way.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import setup, state
from .i18n import _

SITE = "https://iamastealer.github.io/Bashou"
PACKAGE_LOADER = Path("/usr/share/bashou/bashou.bash")
DEBIAN_SOURCES = f"""Types: deb
URIs: {SITE}/deb/
Suites: ./
Signed-By: /etc/apt/keyrings/bashou.asc
"""
REDHAT_REPO = f"""[bashou]
name=Bashou
baseurl={SITE}/rpm/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey={SITE}/bashou.asc
"""


def system():
    """"debian", "redhat", or None where Bashou has no repository."""
    from .challenges import family
    if "debian" in family():
        return "debian"
    if family() & {"rhel", "fedora", "centos"}:
        return "redhat"
    return None


def download(url, dest):
    """The command that fetches `url` into `dest` as root, with curl or wget (None if neither is here)."""
    if shutil.which("curl"):
        return ["sudo", "curl", "-fsSLo", dest, url]
    if shutil.which("wget"):
        return ["sudo", "wget", "-qO", dest, url]
    return None


def plan(kind, folder):
    """The commands, in order. The repository file is written into `folder` first, then installed."""
    if kind == "debian":
        (folder / "bashou.sources").write_text(DEBIAN_SOURCES)
        key = download(f"{SITE}/bashou.asc", "/etc/apt/keyrings/bashou.asc")
        if key is None:
            return None
        return [["sudo", "install", "-d", "-m", "755", "/etc/apt/keyrings"], key,
                ["sudo", "install", "-m", "644", str(folder / "bashou.sources"), "/etc/apt/sources.list.d/bashou.sources"],
                ["sudo", "apt", "update"], ["sudo", "apt", "install", "bashou"]]
    (folder / "bashou.repo").write_text(REDHAT_REPO)
    return [["sudo", "install", "-m", "644", str(folder / "bashou.repo"), "/etc/yum.repos.d/bashou.repo"],
            ["sudo", "dnf", "install", "bashou"]]


def shown(cmd):
    import shlex
    return " ".join(shlex.quote(c) for c in cmd)


def loader_lines(text, old):
    """Indexes of the ~/.bashrc lines that load this git copy (source or ., ~, $HOME or the full path)."""
    home = str(Path.home())
    found = []
    for i, line in enumerate(text.splitlines()):
        m = re.match(r"""\s*(?:source|\.)\s+(['"]?)(.+?)\1\s*(?:#.*)?$""", line)
        if m:
            path = m.group(2).replace("$HOME", home).replace("${HOME}", home)
            if path.startswith("~/"):
                path = home + path[1:]
            if Path(path) == old:
                found.append(i)
    return found


def switch_bashrc(bashrc, old, new=PACKAGE_LOADER):
    """Point ~/.bashrc at the package's loader instead of the git copy. A backup is kept. True if done."""
    try:
        text = bashrc.read_text()
    except FileNotFoundError:
        return False
    lines = text.splitlines()
    found = loader_lines(text, old)
    if not found:
        return False
    shutil.copy(bashrc, bashrc.with_name(bashrc.name + ".bashou-backup"))
    lines[found[0]] = setup.line(new)
    for i in reversed(found[1:]):
        del lines[i]
    bashrc.write_text("\n".join(lines) + "\n")
    return True


def ask(question):
    try:
        return input(f"  {question} [y/N] ").strip().lower() in ("y", "yes", "o", "oui")
    except EOFError:
        return False


def offer(old_loader, bashrc=None, run=subprocess.run, asked=True):
    """Explain, show every command, ask once, run them. 0 when Bashou now comes from the repository."""
    kind = system()
    if kind is None:
        print("  " + _("Bashou has apt and dnf repositories only: on this system, bashou update keeps using git."))
        return 1
    manager = "apt" if kind == "debian" else "dnf"
    print("  " + _("Bashou now has a signed {manager} repository: updates come with the rest of your system "
                   "({manager} upgrade), checked by {manager}. Your pets and progress are kept.").format(manager=manager))
    with tempfile.TemporaryDirectory(prefix="bashou-repo-") as tmp:
        steps = plan(kind, Path(tmp))
        if steps is None:
            print("  " + _("The key is downloaded with curl or wget, and neither is installed."))
            return 1
        bashrc = Path(bashrc or Path.home() / ".bashrc")
        print("  " + _("These commands will run, in this order (sudo asks for your password):"))
        for cmd in steps:
            print(f"    $ {shown(cmd)}")
        print("  " + _("Then in {file}, the line that loads {old} becomes: {new}").format(
            file=bashrc, old=old_loader, new=setup.line(PACKAGE_LOADER)))
        if asked and not ask(_("Go ahead?")):
            print("  " + _("Nothing changed. Later: bashou update --packages"))
            return 2
        for cmd in steps:
            print(f"  $ {shown(cmd)}", flush=True)
            if run(cmd).returncode != 0:
                print("  " + _("That command failed: stopped here. Nothing else was changed."))
                return 1
    if switch_bashrc(bashrc, old_loader):
        print("  " + _("{file} now loads the package (a copy of the old one: {backup}).").format(
            file=bashrc, backup=bashrc.name + ".bashou-backup"))
    else:
        print("  " + _("Load the package from your shell startup file instead of the old copy: {line}").format(
            line=setup.line(PACKAGE_LOADER)))
    print("  " + _("Done! New terminals use the package. Once the old ones are closed, the git copy can go: "
                   "rm -rf {old}").format(old=old_loader.parent))
    with state.locked() as s:
        s["update_available"] = ""
    return 0


def upgrade(run=subprocess.run):
    """A package install: show the command that upgrades it, and run it if you say so."""
    manager = "dnf" if system() == "redhat" else "apt"
    text = "sudo dnf upgrade bashou" if manager == "dnf" else "sudo apt update && sudo apt install --only-upgrade bashou"
    print("  " + _("Bashou came from a package: {manager} updates it, with the rest of your system.").format(manager=manager))
    print(f"    $ {text}")
    if not sys.stdin.isatty() or not ask(_("Run it now?")):
        return 0
    return run(["sh", "-c", text]).returncode
