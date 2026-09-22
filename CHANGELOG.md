# Changelog

Every release has a section here, written for players. CI refuses to tag a release without one
(`python3 tools/changelog.py v1.2.3` prints the section it will publish).

## v0.2.0 — 2026-09-22

### Evolutions
- Every pet now changes shape at each of its 3 stages, with new names: Tadpole → Tree frog → Toad,
  Fennec → Fox → Kitsune, Hatchling → Turtle → Sea turtle, Kit → Beaver → Platypus, and 21 more.
- `bashou evolve` plays the evolution you earned (skip with `s`). In `bashou swap`, `f` shows an
  earlier form of a pet, just for the looks.
- The Kitten starter is now Stardust, which grows into a Planet, then a Star. Saves with the
  Kitten keep their level.
- The tadpole swims instead of breathing, slowly, one stroke at a time.
- `bashou config size large` shows big pixel art where a pet has some: first, a 48-pixel Tarantula.

### New pets and achievements
- Seven new tool pets: Beaver (git), Squirrel (archives), Pigeon (network), Hedgehog (permissions),
  Bee (systemd), Whale (kubectl) and Meerkat (monitoring), with 30 new achievements.
- The Whale only shows up if `kubectl` is installed, and hints and fights only suggest tools you
  have. Adventure questions can still teach tools you don't have yet.
- Pet hints say which achievement they lead to: `(achv: name)`.
- The pet board is more compact and scrolls, so it fits small terminals.

### Languages
- Bashou speaks French: the whole interface, the pets, the achievements and the 166 adventure
  questions (`bashou language`).
- Settings are translated too (`bashou config`).

### Contributing
- Pets, translations and adventure questions are plain JSON files: see `doc/contributing/`.
- The README explains how AI is used in Bashou: to help you learn, not to do it for you.

## v0.1.0 — 2026-09-22

First release: a pet that lives next to your prompt and grows as you learn bash. Starters, pets
unlocked by commands and tools, achievements, fights in a sandbox, security challenges, an adventure
with bosses and questions, and updates from GitHub releases.
