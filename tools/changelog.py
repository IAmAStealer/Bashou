"""python3 tools/changelog.py v1.2.3: print that release's section of CHANGELOG.md (exit 1 if missing).

The release jobs use it for the GitHub release notes, so a release can't be tagged without one.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
HEADER = re.compile(r"^## (v\d+\.\d+\.\d+) — \d{4}-\d{2}-\d{2}$", re.M)


def sections(text):
    """{version: notes} for every "## v1.2.3 — YYYY-MM-DD" section, newest first."""
    found = list(HEADER.finditer(text))
    ends = [m.start() for m in found[1:]] + [len(text)]
    return {m.group(1): text[m.end():end].strip() for m, end in zip(found, ends)}


def main(args):
    if len(args) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    notes = sections(CHANGELOG.read_text()).get(args[0])
    if not notes:
        print(f"CHANGELOG.md has no section for {args[0]}: add '## {args[0]} — YYYY-MM-DD' first.", file=sys.stderr)
        return 1
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
