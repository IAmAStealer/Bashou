"""Pixel art checks: the PNG reader (every row filter editors use) and the rules for art/."""

import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from bashou import art

RED, CLEAR, BLUE = (200, 40, 40, 255), (0, 0, 0, 0), (40, 40, 200, 255)


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def write_png(path, rows, filters=(0,)):
    """RGBA PNG, cycling through the given row filters (like real encoders do)."""
    raw, prev = b"", bytes(len(rows[0]) * 4)
    for y, row in enumerate(rows):
        line = bytes(v for px in row for v in px)
        f = filters[y % len(filters)]
        out = bytearray()
        for x, v in enumerate(line):
            a = line[x - 4] if x >= 4 else 0
            b, c = prev[x], prev[x - 4] if x >= 4 else 0
            pred = [0, a, b, (a + b) // 2, paeth(a, b, c)][f]
            out.append((v - pred) & 255)
        raw += bytes([f]) + bytes(out)
        prev = line
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    ihdr = struct.pack(">IIBBBBB", len(rows[0]), len(rows), 8, 6, 0, 0, 0)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw))
                          + chunk(b"IEND", b""))


def sprite(w, h):
    return [[RED if (x + y) % 3 else (BLUE if x % 2 else CLEAR) for x in range(w)] for y in range(h)]


class ReaderTest(unittest.TestCase):
    def test_every_row_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = sprite(7, 5)
            path = Path(tmp) / "a.png"
            write_png(path, rows, filters=(0, 1, 2, 3, 4))
            self.assertEqual(art.read_png(path), rows)

    def test_not_a_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.png").write_text("hello")
            self.assertTrue(art.problems(Path(tmp) / "a.png"))


class RulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, rel, rows):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        write_png(path, rows, filters=(4, 1))

    def test_a_good_submission(self):
        for pose in art.POSES:
            self.add(f"fox/32/{pose}.png", sprite(30, 24))
        self.add("fox/16/base.png", sprite(16, 12))
        self.assertEqual(art.check(self.root), [])

    def test_mistakes_are_explained(self):
        self.add("fox/32/inhale.png", sprite(40, 20))                    # too big, and no base.png
        self.add("fox/16/base.png", sprite(16, 16))
        self.add("fox/16/walk.png", sprite(16, 16))                      # unknown pose
        self.add("fox/16/left.png", sprite(16, 10))                      # not the same size
        self.add("fox/24/base.png", sprite(8, 8))                        # not a size folder
        soft = sprite(8, 8)
        soft[0][0] = (200, 40, 40, 128)
        self.add("owl/16/base.png", soft)                                # half-transparent
        colors = [[(x * 8, y * 8, 0, 255) for x in range(8)] for y in range(8)]
        self.add("mole/16/base.png", colors)                             # 64 colors
        text = "\n".join(art.check(self.root))
        for bit in ["bigger than 32×32", "base.png is missing", "unknown pose", "same size",
                    "size folders", "half-transparent", "64 colors"]:
            self.assertIn(bit, text)

    def test_the_repo_art_is_valid(self):
        self.assertEqual(art.check(), [])


if __name__ == "__main__":
    unittest.main()
