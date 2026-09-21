"""The world ahead of the hero: sky, a road in perspective, biome scenery growing as it comes closer.

Everything is computed from (biome, distance, time), so the same place always looks the same.
"""

import math
import random

# name: sky top, sky at the horizon, ground (2 shades), road (2 shades), road edge (2 shades)
BIOMES = {
    "meadow": ((110, 170, 235), (190, 225, 250), ((95, 170, 75), (85, 155, 68)),
               ((200, 175, 125), (190, 165, 118)), ((235, 235, 235), (170, 60, 60))),
    "hills": ((120, 160, 225), (240, 205, 170), ((120, 175, 80), (108, 160, 72)),
              ((185, 160, 115), (175, 150, 108)), ((225, 225, 225), (150, 110, 70))),
    "forest": ((80, 130, 180), (160, 200, 190), ((50, 120, 60), (44, 108, 54)),
               ((140, 110, 75), (130, 102, 70)), ((90, 70, 45), (70, 55, 35))),
    "sand": ((90, 160, 230), (250, 225, 170), ((235, 205, 140), (225, 195, 130)),
             ((205, 175, 120), (195, 165, 112)), ((245, 235, 210), (190, 140, 80))),
    "water": ((100, 165, 230), (200, 230, 245), ((50, 110, 190), (45, 100, 175)),
              ((150, 105, 65), (120, 82, 50)), ((95, 65, 40), (95, 65, 40))),
    "dungeon": ((20, 18, 26), (45, 40, 55), ((70, 68, 80), (62, 60, 72)),
                ((95, 92, 105), (85, 82, 95)), ((55, 52, 62), (55, 52, 62))),
}

# Scenery sprites (drawn from their bottom center), per biome.
SPRITES = {
    "tuft": (["..g.g..", ".gGgGg.", "gGgGgGg"], {"g": (70, 150, 60), "G": (120, 200, 90)}),
    "flower": ([".rYr.", "..g..", ".gg.."], {"r": (235, 90, 120), "Y": (250, 220, 90), "g": (70, 150, 60)}),
    "tree": (["...LLL...", "..LLlLL..", ".LLlLLLL.", "LLLLLlLLL", ".LLLLLLL.", "...LLL...",
              "....t....", "....t....", "...ttt..."],
             {"L": (45, 125, 55), "l": (95, 175, 85), "t": (110, 75, 45)}),
    "pine": (["....L....", "...LLL...", "..LLLLL..", "...LLL...", "..LLLLL..", ".LLLLLLL.",
              "LLLLLLLLL", "....t....", "....t...."],
             {"L": (35, 95, 60), "t": (100, 70, 45)}),
    "rock": (["..aaa..", ".aoooa.", "aoolooa", "aaaaaaa"],
             {"a": (95, 95, 105), "o": (140, 140, 150), "l": (180, 180, 190)}),
    "cactus": (["..g..", "g.g..", "g.g.g", "ggggg", "..g..", "..g.."], {"g": (80, 150, 70)}),
    "palm": (["LL.L.LL", ".LLLLL.", "L..t..L", "...t...", "...t...", "..ttt.."],
             {"L": (60, 150, 70), "t": (150, 110, 60)}),
    "reed": (["b.b", "g.g", "ggg", ".g."], {"g": (70, 140, 80), "b": (120, 80, 50)}),
    "lily": (["gggP", ".gg."], {"g": (60, 150, 80), "P": (240, 160, 200)}),
    "torch": (["..Y..", ".YOY.", "..R..", "..b..", "..b..", "..b.."],
              {"Y": (255, 230, 120), "O": (255, 160, 40), "R": (220, 80, 30), "b": (90, 70, 50)}),
    "pillar": (["aaaaa", ".ooo.", ".ooo.", ".ooo.", ".ooo.", ".ooo.", "aaaaa"],
               {"a": (80, 78, 92), "o": (120, 118, 132)}),
}
SCENERY = {
    "meadow": ["tuft", "tuft", "flower", "flower", "tree", "rock"],
    "hills": ["tuft", "rock", "tree", "flower"],
    "forest": ["tree", "pine", "pine", "tuft"],
    "sand": ["cactus", "cactus", "rock", "palm"],
    "water": ["reed", "lily", "lily", "rock"],
    "dungeon": ["torch", "pillar", "torch"],
}

CAMERA = 30.0          # how deep the view is
SPACING = 4            # distance between two scenery objects
FAR = 70.0


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def draw(canvas, biome, distance, t=0.0):
    """Paint the scene for the hero at `distance` (in world units), `t` seconds for animations."""
    sky_top, sky_low, ground, road, edge = BIOMES[biome]
    w, h = canvas.w, canvas.h
    horizon = int(h * 0.38)
    px = canvas.px

    # Sky (or the dungeon's vault), with a few far details.
    for y in range(horizon):
        px[y][:] = [lerp(sky_top, sky_low, y / max(1, horizon - 1))] * w
    backdrop(canvas, biome, horizon, distance, t)

    # Ground, road and road edges: stripes whose phase follows the distance give the motion.
    for y in range(horizon, h):
        near = (y - horizon + 1) / (h - horizon)            # 0 at the horizon, 1 at the bottom
        z = CAMERA / (y - horizon + 0.5)
        band = int((z + distance) * 1.2) % 2
        half = 1 + near * w * 0.30
        edge_w = max(1, near * w * 0.03)
        mid = w / 2
        row = px[y]
        for x in range(w):
            off = abs(x + 0.5 - mid)
            if off < half:
                row[x] = road[band]
            elif off < half + edge_w:
                row[x] = edge[band]
            else:
                row[x] = ground_pixel(biome, ground, band, x, y, z, distance, t, off - half, near)
    objects(canvas, biome, horizon, distance, t)


def backdrop(canvas, biome, horizon, distance, t):
    w, px = canvas.w, canvas.px
    if biome == "dungeon":
        for y in range(horizon):                            # vault bricks
            for x in range(w):
                if (y % 4 == 0) or (x + (y // 4) * 3) % 8 == 0:
                    px[y][x] = (35, 32, 44)
        return
    # sun and two clouds drifting
    sx, sy = int(w * 0.8), max(2, horizon // 4)
    for y in range(sy - 2, sy + 3):
        for x in range(sx - 3, sx + 4):
            if (x - sx) ** 2 / 9 + (y - sy) ** 2 / 4 <= 1 and 0 <= y < horizon:
                px[y][x % w] = (255, 240, 170)
    for i, (cy, speed) in enumerate(((horizon // 3, 0.6), (horizon // 2, 0.35))):
        cx = int((i * w / 2 + t * speed * 2) % (w + 12)) - 6
        for dy, span in ((0, 3), (1, 5)):
            for dx in range(-span, span + 1):
                if 0 <= cx + dx < w and 0 <= cy + dy < horizon:
                    px[cy + dy][cx + dx] = (250, 250, 255)
    # far layer at the horizon
    shade = {"hills": (90, 150, 90), "forest": (30, 80, 45), "sand": (220, 185, 120),
             "meadow": (120, 170, 110), "water": (130, 160, 190)}[biome]
    height = {"hills": 6, "forest": 4, "sand": 3, "meadow": 2, "water": 1}[biome]
    for x in range(w):
        hgt = int(height * (0.6 + 0.4 * math.sin((x + distance * 0.3) / (5 if biome != "forest" else 1.6))))
        for y in range(horizon - hgt, horizon):
            if y >= 0:
                px[y][x] = shade


def ground_pixel(biome, ground, band, x, y, z, distance, t, off_road, near):
    if biome == "water":                                   # waves drifting across
        wave = math.sin(x * 0.35 + (z + distance) * 1.5 + t * 3)
        return (140, 190, 240) if wave > 0.93 else ground[band]
    if biome == "dungeon":                                 # walls rising beside the road
        if off_road > near * 6 + 1:
            brick = int((z + distance) * 2) % 2
            mortar = int(z * 4) % 3 == 0 or (x // 3 + brick) % 4 == 0
            return (50, 45, 55) if mortar else (88, 72, 70)
        return ground[band]
    if biome == "sand" and (x * 7 + int(z * 3)) % 23 == 0:
        return (245, 225, 170)
    return ground[band]


def objects(canvas, biome, horizon, distance, t):
    """Scenery on both sides of the road, from far to near."""
    w, h = canvas.w, canvas.h
    first = int(distance // SPACING) + 1
    for k in range(first + int(FAR // SPACING), first - 1, -1):
        rel = k * SPACING - distance
        if rel <= 0.5:
            continue
        rng = random.Random(f"{biome}:{k}")
        kind = rng.choice(SCENERY[biome])
        rows, palette = SPRITES[kind]
        if kind == "torch" and int(t * 6 + k) % 2:          # flicker
            palette = {**palette, "Y": (255, 200, 90), "O": (240, 120, 30)}
        y = horizon + CAMERA / rel
        if y >= h + 4:
            continue
        near = (y - horizon) / (h - horizon)
        scale = near * 2.2
        if scale < 0.25:
            continue
        side = -1 if rng.random() < 0.5 else 1
        spread = 1 + near * w * 0.30 + near * w * (0.08 + rng.random() * 0.25)
        x = w / 2 + side * spread
        blit(canvas, rows, palette, x, y, scale)


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
