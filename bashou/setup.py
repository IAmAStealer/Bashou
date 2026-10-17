"""`bashou on` (once `bashou setup`) in a shell that didn't load Bashou: the one line in ~/.bashrc (or
~/.zshrc, typed in zsh) that loads it, for you only.

The package turns the pet on by itself (handover.bash), but only where bash reads /etc/profile.d: on Debian
and Ubuntu, login shells only. This line covers the other terminals, and turns the pet back on after a
`bashou off`.
"""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from . import brew, procs, state
from .i18n import _

LOADER = brew.stable(Path(__file__).resolve().parent.parent) / "bashou.bash"   # brew: opt/, not Cellar/
ZSH_LOADER = LOADER.with_suffix(".zsh")
SHELLS = ("bash", "zsh")


def target(shell):
    """(startup file, loader) for `shell`."""
    return (Path.home() / ".zshrc", ZSH_LOADER) if shell == "zsh" else (Path.home() / ".bashrc", LOADER)


def current_shell():
    """The shell you typed the command in: BASHOU_SHELL (the loaders export it), else the first bash or zsh
    up the processes that started this one, else your login shell ($SHELL). bash when nothing says."""
    shell = os.environ.get("BASHOU_SHELL", "")
    if shell in SHELLS:
        return shell
    pid = os.getppid()
    while pid > 1:
        found = procs.parent(pid)
        if found is None:
            break
        if found[1] in SHELLS:
            return found[1]
        pid = found[0]
    shell = Path(os.environ.get("SHELL", "")).name
    return shell if shell in SHELLS else "bash"


def bash_version():
    """(major, minor) of the bash on PATH, (0, 0) when there's none or it doesn't say."""
    try:
        out = subprocess.run(["bash", "-c", 'echo "${BASH_VERSINFO[0]} ${BASH_VERSINFO[1]}"'],
                             capture_output=True, text=True, timeout=5).stdout.split()
        return int(out[0]), int(out[1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return (0, 0)


def bash_ok():
    """Is this bash recent enough for Bashou (4.4: PS0)? macOS's own is 3.2: there, only zsh gets the line."""
    return bash_version() >= (4, 4)


def usable(shell):
    return bool(shutil.which(shell)) and (shell != "bash" or bash_ok())


def line(loader=LOADER):
    return "source " + shlex.quote(str(loader))


def loaded(text):
    """Does ~/.bashrc (~/.zshrc) already load a bashou.bash (bashou.zsh), this one or a git clone's
    (`source ~/.bashou/bashou.bash`)? `bashou on` sets up too, and must not add a second loader."""
    return bool(re.search(r"^\s*(source|\.)\s+\S*bashou\.(bash|zsh)\b", text, re.M))


def append(rc, loader):
    """Add the line that loads `loader` to `rc`, unless it already loads Bashou. True when added."""
    try:
        text = rc.read_text()
    except FileNotFoundError:
        text = ""
    if line(loader) in text.splitlines() or loaded(text):
        return False
    with rc.open("a") as fh:
        fh.write(("" if not text or text.endswith("\n") else "\n") + line(loader) + "\n")
    return True


def run(bashrc=None, loader=None, off=None, shell=None):
    """The line for the shell you typed in, and for the other one when it's installed (owner, 2026-10-12:
    installed from bash, zsh had no pet and no `bashou` command to fix it)."""
    current = shell or current_shell()
    rc, default = target(current)
    bashrc, loader = Path(bashrc or rc), loader or default
    Path(off or state.DATA / "off").unlink(missing_ok=True)     # `bashou off` is over
    if not append(bashrc, loader):
        print("  " + _("Bashou is already in {file}.").format(file=bashrc))
    else:
        print("  " + _("Added to {file}: {line}").format(file=bashrc, line=line(loader)))
        print("  " + _("Open a new terminal (or: source ~/{file}) to meet your pet.").format(file=bashrc.name))
    if bashrc == rc:                                           # not a file given by a test or a caller
        for other in SHELLS:
            if other != current and usable(other):
                other_rc, other_loader = target(other)
                if append(other_rc, other_loader):
                    print("  " + _("Added to {file} too, for {program}: {line}").format(
                        file=other_rc, program=other, line=line(other_loader)))
    return 0


def add_other(shell, data=None):
    """At a start in the other shell: add Bashou to `shell`'s startup file too, once (a file in `data`
    remembers it, so a line you remove stays removed). True when added."""
    done = Path(data or state.DATA) / f"setup.{shell}"
    if done.exists():
        return False
    done.parent.mkdir(parents=True, exist_ok=True)
    done.touch()
    if not usable(shell):
        return False
    rc, loader = target(shell)
    if not append(rc, loader):
        return False
    print("  " + _("You also have {program}: Bashou is now in {file} too, so your pet comes along there.").format(
        program=shell, file=rc))
    return True
