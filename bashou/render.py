"""Draw sprites with half blocks (two pixels per character cell) over the terminal text."""

import unicodedata

ESC = "\x1b"
SKIP = ESC + "[C"   # move right without touching the cell: transparent


def grid(pet, poses, stage=1):
    g = [list(row) for row in pet.base]
    for r, c, k in pet.stages.get(stage, ()):
        g[r][c] = k
    for pose in poses:
        for r, c, k in pet.poses.get(pose, ()):
            g[r][c] = k
    return g


def mask(pet):
    """Cells any pose can paint, plus the particle spot. Everything else stays transparent."""
    g = [list(row) for row in pet.base]
    for pixels in [*pet.poses.values(), *pet.stages.values()]:
        for r, c, _ in pixels:
            g[r][c] = "x"
    rows = []
    for i in range(0, len(g), 2):
        rows.append([g[i][c] != "." or g[i + 1][c] != "." for c in range(pet.width)])
    zr, zc = pet.z_at
    for c in range(zc, min(zc + 3, pet.width)):
        rows[zr][c] = True
    # Enter on an empty line scrolls the screen without erasing us: the old picture moves up a row.
    # Painting every cell above the pet (up to the top of the screen) covers those copies.
    for c in range(pet.width):
        low = max((r for r in range(len(rows)) if rows[r][c]), default=-1)
        for r in range(low):
            rows[r][c] = True
    return rows


def _fg(rgb):
    return "38;2;%d;%d;%d" % rgb


def _bg(rgb):
    return "48;2;%d;%d;%d" % rgb


def lines(pet, poses, cells, stage=1):
    """Sprite lines, ready to print at the sprite's top-left corner."""
    g = grid(pet, poses, stage)
    pal = pet.palette
    out = []
    for i in range(0, len(g), 2):
        line = []
        for c in range(pet.width):
            t, b = g[i][c], g[i + 1][c]
            if t == "." and b == ".":
                line.append(" " if cells[i // 2][c] else SKIP)
            elif t == ".":
                line.append(f"{ESC}[{_fg(pal[b])}m▄{ESC}[0m")
            elif b == ".":
                line.append(f"{ESC}[{_fg(pal[t])}m▀{ESC}[0m")
            else:
                line.append(f"{ESC}[{_fg(pal[t])};{_bg(pal[b])}m▀{ESC}[0m")
        out.append("".join(line))
    return out


def width(text):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def erase(cells, row, col):
    """Blank the given cells (list of rows of booleans) with its top-left at row/col (1-based)."""
    out = []
    for i, cols in enumerate(cells):
        out.append(f"{ESC}[{row + i};{col}H")
        out.append("".join(" " if on else SKIP for on in cols))
    return "".join(out)


def wrap(text, w, max_lines):
    """Split on spaces into lines of at most `w` columns; the last kept line ends with … if cut."""
    lines, cur = [], ""
    for word in text.split(" "):
        while width(word) > w:                           # a word longer than the bubble
            word = word[:-2] + "…"
        if cur and width(cur) + 1 + width(word) > w:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while width(last) > w - 1:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def bubble(text, max_width, max_lines=4):
    """A speech bubble pointing right (wrapped on up to `max_lines` lines), and its width."""
    rows = wrap(text, max(4, max_width - 5), max_lines)
    w = max(width(r) for r in rows)
    body = ["│ " + r + " " * (w - width(r)) + " │" + ("◂" if i == 0 else " ") for i, r in enumerate(rows)]
    return ["╭" + "─" * (w + 2) + "╮ ", *body, "╰" + "─" * (w + 2) + "╯ "], w + 5
