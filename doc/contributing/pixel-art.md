# Pixel art for Bashou

Bashou's pets are small pixel-art sprites drawn in the terminal. There are two ways to help, and
neither needs any code:

1. **Improve a pet in the game today**: edit its text file, `bashou/pets/<pet>.json`.
2. **Draw a bigger version** (16, 32 or 64 px) as PNG files in `art/`. The game will switch to them
   later.

**Who draws what.** `art/` is for **people only**: PNG files drawn by hand, dropped into a pull request
with no programming at all; we turn them into game files. The JSON sprites in `bashou/pets/` go
straight into the game: they may be drawn with an AI, and every one is checked by hand before it's
merged. The exception is the large ones, `bashou/pets/large/`: drawn by a person, like `art/`.

## 1. The pets in the game: `bashou/pets/<pet>.json`

Each pet is one JSON file. The picture is text: one letter per pixel, `.` is transparent. Each
letter's color is set in `palette`. Two pixel rows make one terminal line, so `base` has an even
number of rows (the pets are 17 × 12).

```json
{
 "name": "Tadpole",
 "palette": {"a": "#284830", "o": "#4e7048", "w": "#ffffff", "m": "#191919"},
 "base": [
  ".................",
  "....aaaaa........",
  "..aaoooooaa......",
  ".aowmooooooat...."
 ],
 "poses": {
  "closed": {"3": "---oo------------"},
  "left":   {"3": "---mw------------"}
 },
 "particles": [0, 12]
}
```

- **`poses`** paint over `base`, only on the rows they change: the key is the row number (from 0),
  and in the row, `-` keeps the pixel of `base`. Every pet needs `inhale` (breathing in: the body
  grows by a pixel), `closed` (eyes closed), `left` / `right` (pupils moved) and `fidget` (a small
  move: an ear, a tail, a wing).
- **`stages`** (optional) work the same way, for pixels added when the pet evolves: `"2"` and `"3"`
  (a scarf, a crown…).
- **`particles`**: the terminal line and column of a 3-cell empty spot where `z`, `♪` and `✦` show up.
- **`name`**: the form's name, as players see it (and translated in `bashou/locales/fr.json`).
- **`next`** and **`next_at`**: the form it evolves into, and what it takes: `{"achievements": N}` (that
  many of the pet's family, or all of them once the player has every one they can earn) or `{"level": 3}`
  (the starters). Form k of a pet needs T(k) = (k + 2)² // 4 − 1 achievements: 1, 3, 5, 8, 11, 15, 19, 24,
  29, 35, and a family has exactly T(its forms) achievements (tests/test_families.py): more achievements
  means a new form to draw, fewer means achievements to add. A pet's forms are the chain of these
  links, from its first form (`"first"` in the pet's family file, below) to its last, which has neither.
  A new form is one new file and one link: the board shows one more star, and the tests walk every pet
  through it.
- **`symmetric`** (optional): `true` when the outline is a mirror image. `check` keeps it one.
- **`lone_pixels`** (optional): `true` when pixels touching no other are on purpose (sparkles, spores,
  bubbles). Without it, `check` reports each one as a stray pixel.
- **`idle`** (optional): `"swim"` instead of breathing; the pet then needs `swim_up` and `swim_down`
  poses instead of `inhale` (see `tadpole.json`).

Check your change, and look at every pose in your terminal:

```bash
python3 -m bashou.creatures check        # sizes, colors, poses, particle spot
python3 -m bashou.creatures show fox     # draws base, every pose and stage
```

The same rules as below apply: your own work, readable on dark and light terminals, no pure black
outline.

### Large sprites: `bashou/pets/large/<form>.json`

A form can also have big pixel art, shown to players who run `bashou config size large`. Same JSON
format, any width, an even number of rows. It needs the same poses; they don't have to be eyes: the
large Tarantula has no face, so its "blink" and "look" poses move its legs instead. Everywhere else
(the swap board, evolutions, the adventure) and in terminals too narrow for it, the 17 × 12 sprite
shows. `python3 -m bashou.creatures check` checks both folders; see a large one with
`python3 -m bashou.creatures show large/tarantula`.

### Enemies: `bashou/enemies/<fight id>.json`

The threats of `bashou fight` are drawn next to your pet during the duel. Same format and size as a
pet (17 × 12, the same poses), facing **left**, toward the pet. The file is named after the fight
(`grep_hydra.json` for the Log Hydra); every fight needs one (a test checks it).
Big threats show only their top part, as if the rest were below the frame (the Log Hydra is three
heads on long necks). Check with `python3 -m bashou.creatures check`, see one with
`python3 -m bashou.creatures show ../enemies/grep_hydra`.

### A pet's family: `bashou/families/<pet>.json`

Everything about a pet that isn't a picture lives in one file, named after the pet (`bat.json`), and one
per starter (`star.json`):

- **`name`**, and **`order`**: its place on the board (starters: in the starter choice).
- **`first`**: the sprite of its first form; each form's `next` leads to the others.
- **`unlock`**: how it comes. `{"family_achievement": true}`: the family's first achievement brings it
  (the board shows its first count to reach, like "use find 10 times (3/10)", or the `"how"` sentence when
  there is one). The secret ones: `{"achievement": "fearless"}`, `{"secret_found": true}`, `{"pony": true}`
  (claimed with `bashou pony <id>`, see `bashou/pony.py`).
- **`voice`**, **`tips`** (3 or more) and **`personal`**: what it says. A starter also has a **`blurb`**.
- Optional: **`secret`** (not on the board until found), **`needs`** (hidden where that command isn't
  installed), **`achievement_needs`** (its achievements only count where those commands exist), **`herd`**
  (pets listed together under one line in `bashou pets`, like `"pony"`).

`python3 -m bashou.creatures check` checks the family files too, and the tests walk every pet listed
there: a new pet is a family file and its sprites, with no code to change.

## 2. Bigger art: PNG files in `art/`

### Sizes

Bashou will let players pick the pet size (`16`, `32` or `64` pixels). For now `bashou config size large`
only switches between the 17 × 12 sprites and the large JSON ones above.
In a terminal, one pixel is one column wide and half a line tall:

| Size | Canvas at most | Space in the terminal |
|---|---|---|
| `16` | 16 × 16 px | 16 columns × 8 lines |
| `32` | 32 × 32 px | 32 columns × 16 lines |
| `64` | 64 × 64 px | 64 columns × 32 lines |

Your drawing can be smaller than the canvas (e.g. 30 × 24 in the `32` folder), but not bigger.

### Where the files go

```
art/<pet>/<size>/<pose>.png
art/fox/32/base.png
art/fox/32/closed.png
```

**Pets:** `bat tadpole frog turtle mushroom slime sofa octopus dragon fox owl mole snake ghost spider ant
axolotl gremlin beaver squirrel pigeon hedgehog bee whale meerkat snow_cub snow_leopard mountain_ghost duckling duck white_duck mandarin_duck`, and the starters' forms: `stardust comet star seedling sprout tree pebble golem crystal`.
For a brand new pet, open an issue first so we can agree on how it's unlocked.

**Poses:** in PNG, every pose is a full image of the same size. Only `base` is required, but a pet feels
alive with all of them:

| Pose | What changes |
|---|---|
| `base.png` | the pet at rest (required) |
| `inhale.png` | breathing in: the body grows or rises by a pixel |
| `closed.png` | eyes closed (blinking and sleeping) |
| `left.png` / `right.png` | looking left / right (move the pupils) |
| `fidget.png` | a small movement: ear twitch, tail flick, a wing… |
| `back.png` | seen from behind, for `bashou adventure` (only starters walk there for now) |

### Rules

- **PNG, 8 bits (RGBA or indexed), transparent background.**
- **Every pixel fully opaque or fully transparent**: no anti-aliasing, no soft edges.
- **24 colors at most** per image.
- **Readable on dark and light terminals**: avoid pure black outlines (they vanish on a black
  background); a dark shade of the pet's color works better.
- **Your own work.** No sprites taken from games, sites or other projects, and no tracing. By
  sending it, you agree to share it under the project's MIT license.
- **`art/` and large sprites are drawn by hand.** In `art/` and `bashou/pets/large/`, no AI-generated,
  AI-upscaled or AI-redrawn pixels: the one place Bashou refuses AI help. (The 17 × 12 sprites in
  `bashou/pets/`, and whole new pets at that size, may be made with an AI; a person reviews each one.)

Any pixel-art editor works: [Aseprite](https://www.aseprite.org/),
[LibreSprite](https://libresprite.github.io/), [Piskel](https://www.piskelapp.com/) (in the browser)…
Export each pose as its own PNG, at 1× scale.

### Check it, then send it

```bash
python3 -m bashou.art show art/fox/32/base.png   # see it as Bashou draws it
python3 -m bashou.art check                      # size, colors, transparency, missing poses
```

Then open a pull request with your files and a screenshot of `show` in your terminal. CI runs
`check` too, so a mistake shows up right away on the pull request, with what to fix.

## 3. Light and shading (every sprite)

Owner, 2026-10-28: "lighting could improve a lot". These rules make a small sprite read as a solid
object instead of a flat sticker. They hold for the 17 × 12 sprites and the PNGs alike.

| Rule | How, in pixels | Source |
|---|---|---|
| One light, from the top left | Every sprite is lit from the top left. Highlights go on the faces that look up and left, shadows on the faces that look down and right. Never two light directions in one sprite. | [pixnote: shading](https://pixnote.net/en/learn/shading) |
| Few tones | 17 × 12: a base and one shadow, plus a highlight on what matters (signature feature, eyes). Up to 5 tones (highlight, light, base, shadow, deep shadow) only on a big, round shape. | [pixnote: shading](https://pixnote.net/en/learn/shading) |
| Round shapes follow the form | A cylinder (a tower, a bottle, a neck): vertical bands, the same in every row: light at the left edge, a highlight about a quarter in, the base in the middle, shadow, the darkest band near the right edge, then one lighter column at the very edge (light bounced back from around it). Place the bands by the position in the row's width, not by hand, so they stay vertical when the width changes. A sphere: the same, in rings around a highlight up and left. | [Mallory: shading the sphere](https://marksbymallory.substack.com/p/shading-the-sphere), [BYU: shading cylinders](https://www.designreview.byu.edu/collections/learn-to-sketch-shading-and-shadowing-cylinders) |
| No pillow shading | Don't darken all around the outline with the center brightest: the light then comes from nowhere. Ask "where is the light?" for every shadow. | [pixnote: shading](https://pixnote.net/en/learn/shading) |
| Shift the hue, not only the lightness | Each step toward the shadow turns the hue a little (about 10 to 20°) toward blue or purple, each step toward the light toward yellow; a highlight is near-white and warm. Saturation peaks in the middle tones, lower at both ends. A ramp that only darkens looks flat and muddy. | [Slynyrd: color palettes](https://www.slynyrd.com/blog/2018/1/10/pixelblog-1-color-palettes), [pixnote: color](https://pixnote.net/en/learn/color-palette) |
| Outlines in a dark shade of the object | Not pure black (it vanishes on a black terminal, rule above). At 32 px and up, the outline may be lighter on the lit side (sel-out). | [pixnote: shading](https://pixnote.net/en/learn/shading) |

The Resolver Rook (`bashou/enemies/resolver_rook.json`) is the worked example of a cylinder: the
crown, neck and base each get the same bands, computed from their width.

### Materials that don't follow the one-light rule

Every pixel here is fully on or off, so transparency is shown by contrast and by gaps, never by blending.

| Material | How, in pixels | Source |
|---|---|---|
| Ghost, spirit, flame (lit from inside) | The light comes from the body itself: the brightest tone in a round core in the middle, cooler and darker toward the edges, a pale outline in a dark shade of the ghost color (not black). The bottom fades: darker, ragged, with gaps. No warm top-left highlight: it makes the body look solid. | [Clip Studio: ghost transparency](https://tips.clip-studio.com/en-us/articles/3343), [Graphixly: ghostly character](https://graphixly.com/blogs/news/creating-a-ghostly-character) |
| Eyes on a pale body | The eyes keep the strongest contrast of the sprite: the pixels around them take a darker tone (a socket), never the core or highlight tone, or the white of the eye disappears. | Bashou (owner, 2026-10-28) |
| Glass | Draw the outline and what's behind or inside it, not a fill. One or two sharp highlight pixels at the top left (curved on a round bulb), dark pixels at the edges for contrast. | [Health potion tutorial](https://itch.io/t/2667098/pixel-tutorial-health-potion), [Clip Studio: transparency](https://tips.clip-studio.com/en-us/articles/3384) |
| Liquid in glass | A brighter top surface (light comes from above), a little empty space above it, the surface curved like the container. | [Health potion tutorial](https://itch.io/t/2667098/pixel-tutorial-health-potion) |
| Water | Lighter at the surface and where it spills, darker with depth; reflections broken into short horizontal lines; a few sparkle pixels, not many. | [Slynyrd: water in motion](https://www.slynyrd.com/blog/2018/10/12/pixelblog-10-water-in-motion) |
