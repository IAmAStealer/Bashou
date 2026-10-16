"""CHANGELOG.md sections: the release notes CI publishes, `bashou update` shows and `bashou changelog` lists."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HEADER = re.compile(r"^## (v\d+\.\d+\.\d+) — \d{4}-\d{2}-\d{2}$", re.M)


def sections(text):
    """{version: notes} for every "## v1.2.3 — YYYY-MM-DD" section, newest first."""
    found = list(HEADER.finditer(text))
    ends = [m.start() for m in found[1:]] + [len(text)]
    return {m.group(1): text[m.end():end].strip() for m, end in zip(found, ends)}


def items(text):
    """Release notes as a list: "### Title" headings and "- " entries, wrapped lines joined back."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            out.append(line.lstrip("#").strip() + ":")
        elif line.startswith(("- ", "* ")):
            out.append("• " + line[2:])
        elif line and out and out[-1].startswith("• "):
            out[-1] += " " + line
        elif line:
            out.append(line)
    return out


def notes(root, version):
    """That release's notes from `root`/CHANGELOG.md, or "" (no file, no section)."""
    try:
        return sections((Path(root) / "CHANGELOG.md").read_text()).get(version, "")
    except OSError:
        return ""


def text(root, version=None):
    """Every release (or one), newest first, for players: the maintainers' note at the top left out."""
    try:
        found = sections((Path(root) / "CHANGELOG.md").read_text())
    except OSError:
        return None
    if version:
        found = {version: found[version]} if version in found else {}
    from .render import BOLD, RESET
    out = []
    for v, notes in found.items():
        out.append(f"{BOLD}{v}{RESET}")
        out += ["  " + line for line in items(notes)] + [""]
    return "\n".join(out)


def main(version=None):
    """`bashou changelog [vX.Y.Z]`: through `less` in a terminal (q quits), printed otherwise."""
    from .i18n import _
    ROOT = Path(__file__).resolve().parent.parent
    shown = text(ROOT, version)
    if not shown:
        print("  " + (_("No release {version} in the changelog.").format(version=version) if version
                      else _("The changelog isn't installed with this copy of Bashou.")))
        return 1
    try:
        terminal = os.isatty(sys.stdout.fileno())              # a real one: tests replace stdout
    except (AttributeError, OSError, ValueError):
        terminal = False
    if terminal and shutil.which("less"):
        subprocess.run(["less", "-R"], input=shown, text=True)
    else:
        print(shown)
    return 0
