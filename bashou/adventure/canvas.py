"""A pixel buffer drawn with half blocks (two pixels per terminal cell), redrawing only what changed."""

ESC = "\x1b"


class Canvas:
    def __init__(self, width, height):
        self.w, self.h = width, height - height % 2
        self.px = [[(0, 0, 0)] * self.w for _ in range(self.h)]
        self.shown = {}                 # (line, col) -> (top, bottom) on screen

    def fill(self, color):
        for row in self.px:
            row[:] = [color] * self.w

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = color

    def rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(self.h, y1)):
            row = self.px[y]
            for x in range(max(0, x0), min(self.w, x1)):
                row[x] = color

    def sprite(self, rows, palette, x0, y0, scale=1, flip=False):
        """Draw a sprite (strings, '.' transparent) with its top-left at x0, y0, scaled by an int."""
        for r, line in enumerate(rows):
            for c, ch in enumerate(line[::-1] if flip else line):
                if ch == "." or ch not in palette:
                    continue
                color = palette[ch]
                for dy in range(scale):
                    for dx in range(scale):
                        self.set(x0 + c * scale + dx, y0 + r * scale + dy, color)

    def render(self, top=1, force=False, hide=None):
        """Escape sequence for the cells that changed since the last render (all of them if `force`).
        `hide` = (first line, last line, first col, last col), 0-based: a box drawn over the canvas.
        Cells under it are left alone, so nothing flashes there before the box covers it again."""
        if force:
            self.shown = {}
        out, last = [], None
        for line in range(self.h // 2):
            up, down = self.px[2 * line], self.px[2 * line + 1]
            under = hide and hide[0] <= line <= hide[1]
            for col in range(self.w):
                if under and hide[2] <= col <= hide[3]:
                    continue
                cell = (up[col], down[col])
                if self.shown.get((line, col)) == cell:
                    continue
                self.shown[(line, col)] = cell
                if last != (line, col - 1):
                    out.append(f"{ESC}[{top + line};{col + 1}H")
                if cell[0] == cell[1]:
                    out.append(f"{ESC}[48;2;{cell[0][0]};{cell[0][1]};{cell[0][2]}m ")
                else:
                    out.append(f"{ESC}[38;2;{cell[0][0]};{cell[0][1]};{cell[0][2]};"
                               f"48;2;{cell[1][0]};{cell[1][1]};{cell[1][2]}m▀")
                last = (line, col)
        if out:
            out.append(f"{ESC}[0m")
        return "".join(out)
