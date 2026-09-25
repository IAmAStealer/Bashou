"""Every page of the lessons as plain text, the way an 80×24 terminal shows it (the owl is drawn with #).

    python3 tools/lesson_preview.py                    # every lesson
    python3 tools/lesson_preview.py stack_heap pipes   # some of them
    python3 tools/lesson_preview.py --lang fr pipes    # a translation
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bashou import lesson  # noqa: E402
from bashou.lesson import reader  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def screen(le, n, cols=80, lines=24):
    grid = [[" "] * cols for _ in range(lines)]
    for row, col, text in reader.page_screen(le, n, cols, lines):
        c = col - 1
        for ch in ANSI.sub("", text).replace("▀", "#").replace("▄", "#"):
            if 0 <= row - 1 < lines and c < cols:
                grid[row - 1][c] = ch
            c += 1
    return "\n".join("".join(r).rstrip() for r in grid).rstrip()


def main(args):
    lang = "en"
    if "--lang" in args:
        i = args.index("--lang")
        lang, args = args[i + 1], args[:i] + args[i + 2:]
    for le in lesson.load(lang):
        if not args or le["id"] in args:
            for n in range(len(le["pages"])):
                print(f"==== {le['id']} page {n + 1}/{len(le['pages'])}")
                print(screen(le, n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
