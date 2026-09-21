"""The world around the hero: a calm, dark place, a strip of ground and grass swaying beside the pet.

Everything is computed from (biome, time), so the same place always looks the same.
"""

import math

# name: background (top, bottom), ground, grass (dark, light)
BIOMES = {
    "meadow": ((10, 14, 22), (18, 28, 30), (24, 44, 26), ((50, 110, 50), (95, 170, 80))),
    "hills": ((12, 12, 24), (26, 26, 34), (34, 46, 28), ((70, 115, 55), (120, 165, 85))),
    "forest": ((6, 12, 12), (12, 24, 20), (18, 36, 22), ((30, 90, 50), (70, 140, 80))),
    "sand": ((14, 12, 22), (34, 28, 30), (60, 50, 34), ((150, 130, 70), (205, 180, 110))),
    "water": ((8, 12, 26), (14, 26, 42), (18, 36, 60), ((60, 120, 110), (110, 170, 150))),
    "dungeon": ((8, 7, 10), (20, 18, 24), (36, 34, 42), ((70, 68, 80), (100, 98, 110))),
}
BLADES = 7              # grass blades on each side of the pet


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def draw(canvas, biome, distance=0.0, t=0.0, hero_w=17):
    """Paint the scene; `hero_w` is the pet's width in pixels (it stands at the bottom center)."""
    top, bottom, ground, grass = BIOMES[biome]
    w, h, px = canvas.w, canvas.h, canvas.px
    floor = h - 3
    for y in range(floor):
        px[y][:] = [lerp(top, bottom, y / max(1, floor - 1))] * w
    for y in range(floor, h):
        px[y][:] = [ground] * w
    mid = w // 2
    for side in (-1, 1):
        for i in range(BLADES):
            x = mid + side * (hero_w // 2 + 1 + i * 2 + (i * 7 + (side > 0)) % 2)
            tall = 3 + (i * 5 + (side > 0) * 3) % 5
            sway = math.sin(t * 1.6 + i * 0.9 + side) * 1.5
            color = grass[(i + (side > 0)) % 2]
            for k in range(tall):
                bend = round(sway * (k / tall) ** 2)
                canvas.set(x + bend, floor - k, color)


CAMERA = 30.0          # how deep the view is, for things coming closer on the road
FAR = 70.0


def blit(canvas, rows, palette, cx, bottom, scale):
    """Draw a sprite scaled by any factor (nearest pixel), anchored at its bottom center."""
    sw, sh = len(rows[0]), len(rows)
    tw, th = max(1, round(sw * scale)), max(1, round(sh * scale))
    x0, y0 = int(cx - tw / 2), int(bottom - th)
    for ty in range(th):
        line = rows[min(sh - 1, int(ty / scale))]
        for tx in range(tw):
            ch = line[min(sw - 1, int(tx / scale))]
            if ch != "." and ch in palette:
                canvas.set(x0 + tx, y0 + ty, palette[ch])
