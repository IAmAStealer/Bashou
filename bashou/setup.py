"""`bashou on` (once `bashou setup`) in a shell that didn't load Bashou: the one line in ~/.bashrc (or
~/.zshrc, typed in zsh) that loads it, for you only.

The package turns the pet on by itself (handover.bash), but only where bash reads /etc/profile.d: on Debian
and Ubuntu, login shells only. This line covers the other terminals, and turns the pet back on after a
`bashou off`.
"""

import os
import re
import shlex
from pathlib import Path

from . import state
from .i18n import _

LOADER = Path(__file__).resolve().parent.parent / "bashou.bash"
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
        try:
            name = Path(f"/proc/{pid}/comm").read_text().strip()
            if name in SHELLS:
                return name
            pid = int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    shell = Path(os.environ.get("SHELL", "")).name
    return shell if shell in SHELLS else "bash"


def line(loader=LOADER):
    return "source " + shlex.quote(str(loader))


def loaded(text):
    """Does ~/.bashrc (~/.zshrc) already load a bashou.bash (bashou.zsh), this one or a git clone's
    (`source ~/.bashou/bashou.bash`)? `bashou on` sets up too, and must not add a second loader."""
    return bool(re.search(r"^\s*(source|\.)\s+\S*bashou\.(bash|zsh)\b", text, re.M))


def run(bashrc=None, loader=None, off=None, shell=None):
    rc, default = target(shell or current_shell())
    bashrc, loader = Path(bashrc or rc), loader or default
    Path(off or state.DATA / "off").unlink(missing_ok=True)     # `bashou off` is over
    try:
        text = bashrc.read_text()
    except FileNotFoundError:
        text = ""
    if line(loader) in text.splitlines() or loaded(text):
        print("  " + _("Bashou is already in {file}.").format(file=bashrc))
        return 0
    with bashrc.open("a") as fh:
        fh.write(("" if not text or text.endswith("\n") else "\n") + line(loader) + "\n")
    print("  " + _("Added to {file}: {line}").format(file=bashrc, line=line(loader)))
    print("  " + _("Open a new terminal (or: source ~/{file}) to meet your pet.").format(file=bashrc.name))
    return 0
