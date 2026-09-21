# Pixel art for Bashou

Bashou's pets are small pixel-art sprites drawn in the terminal. You can redraw an existing pet, or
draw it in a bigger size, and send it as a pull request. We will switch the game over to the new art
later.

## Sizes

Bashou will let players pick the pet size (`16`, `32` or `64` pixels; the setting isn't there yet).
In a terminal, one pixel is one column wide and half a line tall:

| Size | Canvas at most | Space in the terminal |
|---|---|---|
| `16` | 16 × 16 px | 16 columns × 8 lines |
| `32` | 32 × 32 px | 32 columns × 16 lines |
| `64` | 64 × 64 px | 64 columns × 32 lines |

Your drawing can be smaller than the canvas (e.g. 30 × 24 in the `32` folder), but not bigger.

## Where the files go

```
art/<pet>/<size>/<pose>.png
art/fox/32/base.png
art/fox/32/closed.png
```

**Pets:** `bat frog turtle mushroom slime sofa octopus dragon fox owl mole snake ghost spider ant
axolotl gremlin`, and the starters' forms: `kitten cat lion seedling sprout tree pebble golem crystal`.
For a brand new pet, open an issue first so we can agree on how it's unlocked.

**Poses:** every pose is a full image of the same size. Only `base` is required, but a pet feels
alive with all of them:

| Pose | What changes |
|---|---|
| `base.png` | the pet at rest (required) |
| `inhale.png` | breathing in: the body grows or rises by a pixel |
| `closed.png` | eyes closed (blinking and sleeping) |
| `left.png` / `right.png` | looking left / right (move the pupils) |
| `fidget.png` | a small movement: ear twitch, tail flick, a wing… |

## Rules

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

## Check it, then send it

```bash
python3 -m bashou.art show art/fox/32/base.png   # see it as Bashou draws it
python3 -m bashou.art check                      # size, colors, transparency, missing poses
```

Then open a pull request with your files and a screenshot of `show` in your terminal. CI runs
`check` too, so a mistake shows up right away on the pull request, with what to fix.
