"""`bashou on` (once `bashou setup`) in a shell that didn't load Bashou: the one line in ~/.bashrc that
loads it, for you only.

The package turns the pet on by itself (handover.bash), but only where bash reads /etc/profile.d: on Debian
and Ubuntu, login shells only. This line covers the other terminals, and turns the pet back on after a
`bashou off`.
"""

import re
import shlex
from pathlib import Path

from . import state
from .i18n import _

LOADER = Path(__file__).resolve().parent.parent / "bashou.bash"


def line(loader=LOADER):
    return "source " + shlex.quote(str(loader))


def loaded(text):
    """Does ~/.bashrc already load a bashou.bash, this one or a git clone's (`source ~/.bashou/bashou.bash`)?
    `bashou on` sets up too, and must not add a second loader."""
    return bool(re.search(r"^\s*(source|\.)\s+\S*bashou\.bash\b", text, re.M))


def run(bashrc=None, loader=LOADER, off=None):
    bashrc = Path(bashrc or Path.home() / ".bashrc")
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
    print("  " + _("Open a new terminal (or: source ~/.bashrc) to meet your pet."))
    return 0
