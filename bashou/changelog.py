"""CHANGELOG.md sections: the release notes CI publishes and `bashou update` shows."""

import re
from pathlib import Path

HEADER = re.compile(r"^## (v\d+\.\d+\.\d+) — \d{4}-\d{2}-\d{2}$", re.M)


def sections(text):
    """{version: notes} for every "## v1.2.3 — YYYY-MM-DD" section, newest first."""
    found = list(HEADER.finditer(text))
    ends = [m.start() for m in found[1:]] + [len(text)]
    return {m.group(1): text[m.end():end].strip() for m, end in zip(found, ends)}


def notes(root, version):
    """That release's notes from `root`/CHANGELOG.md, or "" (no file, no section)."""
    try:
        return sections((Path(root) / "CHANGELOG.md").read_text()).get(version, "")
    except OSError:
        return ""
