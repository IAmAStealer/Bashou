"""A small QR code encoder for `bashou share`: byte mode, error correction level L, versions 1 to 10.

No dependency, nothing leaves the machine: the code is drawn in the terminal for a phone to scan.
Follows ISO/IEC 18004 (the same steps as every encoder: data bits, Reed-Solomon, placement, mask).
"""

# Level L, per version: (error correction codewords per block, [(blocks, data codewords per block), ...])
BLOCKS = {
    1: (7, [(1, 19)]), 2: (10, [(1, 34)]), 3: (15, [(1, 55)]), 4: (20, [(1, 80)]), 5: (26, [(1, 108)]),
    6: (18, [(2, 68)]), 7: (20, [(2, 78)]), 8: (24, [(2, 97)]), 9: (30, [(2, 116)]), 10: (18, [(2, 68), (2, 69)]),
}
ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42],
         9: [6, 26, 46], 10: [6, 28, 50]}
MASKS = [
    lambda r, c: (r + c) % 2 == 0, lambda r, c: r % 2 == 0, lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0, lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: r * c % 2 + r * c % 3 == 0, lambda r, c: (r * c % 2 + r * c % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + r * c % 3) % 2 == 0,
]

# Galois field GF(256) with the QR polynomial x^8 + x^4 + x^3 + x^2 + 1.
EXP, LOG = [0] * 512, [0] * 256
_x = 1
for _i in range(255):
    EXP[_i], LOG[_x] = _x, _i
    _x = (_x << 1) ^ (0x11D if _x & 0x80 else 0)
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def data_capacity(version):
    ec, groups = BLOCKS[version]
    return sum(n * size for n, size in groups)


def reed_solomon(data, n):
    """The n error correction codewords of `data`."""
    gen = [1]
    for i in range(n):                                  # (x - a^0)(x - a^1)…(x - a^(n-1))
        gen = [a ^ (EXP[LOG[b] + i] if b else 0) for a, b in zip(gen + [0], [0] + gen)]
    rest = list(data) + [0] * n
    for i in range(len(data)):
        coef = rest[i]
        if coef:
            for j in range(1, n + 1):
                if gen[j]:
                    rest[i + j] ^= EXP[LOG[gen[j]] + LOG[coef]]
    return rest[len(data):]


def codewords(data, version):
    """Data bits (byte mode), padded, split into blocks, with error correction, interleaved."""
    bits = [0, 1, 0, 0]                                 # byte mode
    count = 8 if version < 10 else 16
    bits += [(len(data) >> i) & 1 for i in reversed(range(count))]
    for byte in data:
        bits += [(byte >> i) & 1 for i in reversed(range(8))]
    capacity = data_capacity(version) * 8
    bits += [0] * min(4, capacity - len(bits))          # terminator
    bits += [0] * (-len(bits) % 8)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = [0xEC, 0x11]
    words += [pad[i % 2] for i in range(data_capacity(version) - len(words))]
    ec, groups = BLOCKS[version]
    blocks, at = [], 0
    for n, size in groups:
        for _ in range(n):
            blocks.append(words[at:at + size])
            at += size
    ecs = [reed_solomon(b, ec) for b in blocks]
    out = []
    for i in range(max(map(len, blocks))):
        out += [b[i] for b in blocks if i < len(b)]
    for i in range(ec):
        out += [e[i] for e in ecs]
    return out


def bch(value, poly, bits):
    """value followed by its BCH remainder (format and version information)."""
    rest = value << bits
    top = poly.bit_length() - 1
    for i in reversed(range(bits, rest.bit_length())):
        if rest >> i & 1:
            rest ^= poly << (i - top)
    return value << bits | rest


class Matrix:
    def __init__(self, version):
        self.version, self.size = version, 17 + 4 * version
        self.dark = [[False] * self.size for _ in range(self.size)]
        self.fixed = [[False] * self.size for _ in range(self.size)]

    def set(self, r, c, dark):
        self.dark[r][c], self.fixed[r][c] = dark, True

    def functions(self):
        n = self.size
        for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):               # finders and their white border
            for r in range(-1, 8):
                for c in range(-1, 8):
                    if 0 <= r0 + r < n and 0 <= c0 + c < n:
                        ring = max(abs(r - 3), abs(c - 3))
                        self.set(r0 + r, c0 + c, ring != 2 and ring != 4)
        for i in range(8, n - 8):                                      # timing
            self.set(6, i, i % 2 == 0)
            self.set(i, 6, i % 2 == 0)
        pos = ALIGN[self.version]
        last = len(pos) - 1
        for i, r in enumerate(pos):
            for j, c in enumerate(pos):
                if (i, j) not in ((0, 0), (0, last), (last, 0)):           # not on the finders
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            self.set(r + dr, c + dc, max(abs(dr), abs(dc)) != 1)
        self.format(0)                                                 # reserve; written for real later
        if self.version >= 7:
            info = bch(self.version, 0x1F25, 12)
            for i in range(18):
                dark = bool(info >> i & 1)
                self.set(n - 11 + i % 3, i // 3, dark)
                self.set(i // 3, n - 11 + i % 3, dark)

    def format(self, mask):
        n = self.size
        info = bch(0b01 << 3 | mask, 0x537, 10) ^ 0x5412              # 01 = level L
        bit = [bool(info >> i & 1) for i in range(15)]
        for i in range(6):                                             # around the top-left finder
            self.set(i, 8, bit[i])
        self.set(7, 8, bit[6])
        self.set(8, 8, bit[7])
        self.set(8, 7, bit[8])
        for i in range(9, 15):
            self.set(8, 14 - i, bit[i])
        for i in range(8):                                             # the copy, split in two
            self.set(8, n - 1 - i, bit[i])
        for i in range(8, 15):
            self.set(n - 15 + i, 8, bit[i])
        self.set(n - 8, 8, True)                                       # the dark module

    def place(self, words):
        bits = [(w >> i) & 1 for w in words for i in reversed(range(8))]
        n, at, right = self.size, 0, self.size - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(n):
                for j in range(2):
                    c = right - j
                    up = (right + 1) & 2 == 0
                    r = n - 1 - vert if up else vert
                    if not self.fixed[r][c] and at < len(bits):
                        self.dark[r][c] = bool(bits[at])
                        at += 1
            right -= 2

    def apply(self, mask):
        f = MASKS[mask]
        for r in range(self.size):
            for c in range(self.size):
                if not self.fixed[r][c] and f(r, c):
                    self.dark[r][c] = not self.dark[r][c]

    def penalty(self):
        n, d, score = self.size, self.dark, 0
        lines = d + [list(col) for col in zip(*d)]
        for line in lines:                                             # 1: runs of 5+ of one color
            run = 1
            for i in range(1, n + 1):
                if i < n and line[i] == line[i - 1]:
                    run += 1
                else:
                    if run >= 5:
                        score += run - 2
                    run = 1
        for r in range(n - 1):                                         # 2: 2x2 blocks of one color
            for c in range(n - 1):
                if d[r][c] == d[r][c + 1] == d[r + 1][c] == d[r + 1][c + 1]:
                    score += 3
        core = [True, False, True, True, True, False, True]
        for line in lines:                                             # 3: finder-like 1:1:3:1:1 next to 4 light
            padded = [False] * 4 + line + [False] * 4
            for i in range(len(padded) - 10):
                window = padded[i:i + 11]
                if window == [False] * 4 + core or window == core + [False] * 4:
                    score += 40
        dark = sum(map(sum, d))                                        # 4: balance of dark and light
        score += abs(dark * 20 - n * n * 10) // (n * n) * 10
        return score


def encode(text, mask=None):
    """The QR code of `text` as rows of booleans (True = dark), without the quiet zone."""
    data = text.encode("utf-8")
    for version in BLOCKS:
        header = 4 + (8 if version < 10 else 16)
        if header + 8 * len(data) <= data_capacity(version) * 8:
            break
    else:
        raise ValueError(f"too long for a QR code up to version 10: {len(data)} bytes")
    words = codewords(data, version)
    best = None
    for m in ([mask] if mask is not None else range(8)):
        mx = Matrix(version)
        mx.functions()
        mx.place(words)
        mx.apply(m)
        mx.format(m)
        score = mx.penalty()
        if best is None or score < best[0]:
            best = (score, mx)
    return best[1].dark


def terminal(rows, quiet=4):
    """Two rows per line with ▀, black on white whatever the terminal's theme (phones need dark on light)."""
    n = len(rows)
    grid = [[False] * (n + 2 * quiet) for _ in range(quiet)]
    grid += [[False] * quiet + list(r) + [False] * quiet for r in rows]
    grid += [[False] * (n + 2 * quiet) for _ in range(quiet + 1)]
    out = []
    for y in range(0, n + 2 * quiet, 2):
        line = []
        for top, bottom in zip(grid[y], grid[y + 1]):
            line.append(f"\x1b[{30 if top else 97};{40 if bottom else 107}m▀")
        out.append("".join(line) + "\x1b[0m")
    return out
