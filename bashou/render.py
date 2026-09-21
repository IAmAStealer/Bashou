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


def bubble(text, max_width):
    """Three lines of a speech bubble pointing right, and its width."""
    while width(text) > max_width - 5 and len(text) > 1:
        text = text[:-2] + "…"
    w = width(text)
    return ["╭" + "─" * (w + 2) + "╮ ",
            "│ " + text + " │◂",
            "╰" + "─" * (w + 2) + "╯ "], w + 5
