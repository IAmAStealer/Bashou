# Pixel art for Bashou

Bashou's pets are small pixel-art sprites drawn in the terminal. There are two ways to help, and
neither needs any code:

1. **Improve a pet in the game today**: edit its text file, `bashou/pets/<pet>.json`.
2. **Draw a bigger version** (16, 32 or 64 px) as PNG files in `art/`. The game will switch to them
   later.

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
(`grep_hydra.json` for the Log Hydra); a fight without one shows a tinted placeholder monster.
Big threats show only their top part, as if the rest were below the frame (the Log Hydra is three
heads on long necks). Check with `python3 -m bashou.creatures check`, see one with
`python3 -m bashou.creatures show ../enemies/grep_hydra`.

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
axolotl gremlin beaver squirrel pigeon hedgehog bee whale meerkat`, and the starters' forms: `stardust comet star seedling sprout tree pebble golem crystal`.
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
