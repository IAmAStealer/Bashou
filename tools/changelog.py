"""python3 tools/changelog.py v1.2.3: print that release's section of CHANGELOG.md (exit 1 if missing).

The release jobs use it for the GitHub release notes, so a release can't be tagged without one.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bashou.changelog import notes, sections  # noqa: E402,F401

CHANGELOG = ROOT / "CHANGELOG.md"


def main(args):
    if len(args) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    text = notes(ROOT, args[0])
    if not text:
        print(f"CHANGELOG.md has no section for {args[0]}: add '## {args[0]} — YYYY-MM-DD' first.", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
