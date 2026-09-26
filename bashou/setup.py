"""`bashou on` (once `bashou setup`): the one line in ~/.bashrc that loads Bashou, for you only.

A package installs Bashou for the whole machine but turns it on for nobody: each user opts in.
"""

import re
import shlex
from pathlib import Path

from .i18n import _

LOADER = Path(__file__).resolve().parent.parent / "bashou.bash"


def line(loader=LOADER):
    return "source " + shlex.quote(str(loader))


def loaded(text):
    """Does ~/.bashrc already load a bashou.bash, this one or a git clone's (`source ~/.bashou/bashou.bash`)?
    `bashou on` sets up too, and must not add a second loader."""
    return bool(re.search(r"^\s*(source|\.)\s+\S*bashou\.bash\b", text, re.M))


def run(bashrc=None, loader=LOADER):
    bashrc = Path(bashrc or Path.home() / ".bashrc")
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
    print("  " + _("Open a new terminal (or: source ~/.bashrc) to meet your pet."))
    return 0
