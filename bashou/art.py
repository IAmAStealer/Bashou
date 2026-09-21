"""Pixel art sent as PNG files (see doc/contributing/pixel-art.md).

    python3 -m bashou.art show art/fox/32/base.png    # preview in the terminal, as Bashou draws it
    python3 -m bashou.art check                       # check every file in art/ (CI runs it too)

A small PNG reader (standard library only): 8-bit RGBA, RGB or indexed images, not interlaced,
which is what pixel-art editors (Aseprite, Piskel, LibreSprite…) export.
"""

import struct
import sys
import zlib
from pathlib import Path

ART = Path(__file__).resolve().parent.parent / "art"
SIZES = (16, 32, 64)
POSES = ("base", "inhale", "closed", "left", "right", "fidget", "back")
MAX_COLORS = 24


class ArtError(ValueError):
    pass


def read_png(path):
    """Rows of (r, g, b, a) tuples."""
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ArtError("not a PNG file")
    pos, chunks = 8, {}
    idat = b""
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IDAT":
            idat += body
        else:
            chunks.setdefault(kind, body)
    width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", chunks[b"IHDR"])
    if depth != 8 or interlace or color not in (2, 3, 6):
        raise ArtError("save it as an 8-bit RGBA (or indexed) PNG, not interlaced")
    channels = {2: 3, 3: 1, 6: 4}[color]
    raw = zlib.decompress(idat)
    stride = width * channels
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(height):
        kind, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b, c = prev[x], prev[x - channels] if x >= channels else 0
            if kind == 1:
                line[x] = (line[x] + a) & 255
            elif kind == 2:
                line[x] = (line[x] + b) & 255
            elif kind == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        rows.append(bytes(line))
    if color == 3:
        plte, trns = chunks[b"PLTE"], chunks.get(b"tRNS", b"")
        palette = [(*plte[j * 3:j * 3 + 3], trns[j] if j < len(trns) else 255) for j in range(len(plte) // 3)]
        return [[palette[v] for v in row] for row in rows]
    if color == 2:
        return [[(*row[x:x + 3], 255) for x in range(0, stride, 3)] for row in rows]
    return [[tuple(row[x:x + 4]) for x in range(0, stride, 4)] for row in rows]


def problems(path, size=None):
    """What's wrong with one image (empty list: fine)."""
    try:
        img = read_png(path)
    except (ArtError, KeyError, zlib.error, struct.error, IndexError) as e:
        return [f"can't read it: {e}"]
    found = []
    height, width = len(img), len(img[0]) if img else 0
    if size and (width > size or height > size):
        found.append(f"{width}×{height} is bigger than {size}×{size}")
    if max(width, height) > max(SIZES):
        found.append(f"{width}×{height}: {max(SIZES)}×{max(SIZES)} at most")
    if any(p[3] not in (0, 255) for row in img for p in row):
        found.append("half-transparent pixels: each pixel must be fully opaque or fully transparent")
    colors = {p[:3] for row in img for p in row if p[3]}
    if len(colors) > MAX_COLORS:
        found.append(f"{len(colors)} colors: {MAX_COLORS} at most")
    return found


def check(root=ART):
    """Every problem in the art folder, as "path: problem" lines."""
    found = []
    for pet in sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []:
        for folder in sorted(p for p in pet.iterdir() if p.is_dir()):
            where = folder.relative_to(root)
            if folder.name not in {str(s) for s in SIZES}:
                found.append(f"{where}: size folders are {', '.join(map(str, SIZES))}")
                continue
            files = sorted(folder.glob("*.png"))
            names = {f.stem for f in files}
            if "base" not in names:
                found.append(f"{where}: base.png is missing")
            found += [f"{where}/{f.name}: unknown pose (use {', '.join(POSES)})" for f in files if f.stem not in POSES]
            dims = set()
            for f in files:
                found += [f"{where}/{f.name}: {p}" for p in problems(f, int(folder.name))]
                try:
                    img = read_png(f)
                    dims.add((len(img[0]), len(img)))
                except (ArtError, KeyError, zlib.error, struct.error, IndexError):
                    pass
            if len(dims) > 1:
                found.append(f"{where}: every pose must have the same size ({', '.join(f'{w}×{h}' for w, h in sorted(dims))})")
    return found


def show(path):
    """Print the image with half blocks, two pixel rows per terminal line."""
    img = read_png(path)
    if len(img) % 2:
        img.append([(0, 0, 0, 0)] * len(img[0]))
    for y in range(0, len(img), 2):
        line = []
        for top, bottom in zip(img[y], img[y + 1]):
            if not top[3] and not bottom[3]:
                line.append(" ")
            elif not top[3]:
                line.append("\033[38;2;%d;%d;%dm▄\033[0m" % bottom[:3])
            elif not bottom[3]:
                line.append("\033[38;2;%d;%d;%dm▀\033[0m" % top[:3])
            else:
                line.append("\033[38;2;%d;%d;%d;48;2;%d;%d;%dm▀\033[0m" % (*top[:3], *bottom[:3]))
        print("".join(line))


def main():
    args = sys.argv[1:]
    if args[:1] == ["show"] and len(args) == 2:
        show(args[1])
        for p in problems(args[1]):
            print(f"⚠ {p}")
        return 0
    if args[:1] == ["check"]:
        found = check(Path(args[1]) if len(args) > 1 else ART)
        for line in found:
            print(line)
        print("art: OK" if not found else f"art: {len(found)} problem(s)")
        return 1 if found else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
