# Changelog

Every release has a section here, written for players. CI refuses to tag a release without one
(`python3 tools/changelog.py v1.2.3` prints the section it will publish).

## v0.2.3 — 2026-09-22

- Every threat of `bashou fight` has its own look: the Log Hydra, the Ledger Golem, the Maze Wraith,
  the Echo Swarm, the Typo Serpent, the Process Phantom and the Knot Eel.

## v0.2.2 — 2026-09-22

- `bashou version` says which version you have, and if a newer one is out.
- `bashou update` lists what's new, one entry per line.
- Ctrl+L starts the prompt below your pet too, like `clear` does.
- `bashou fight` is a duel: the task, your pet with 3 hearts and the enemy are drawn at the top, where
  your pet lives. A successful command with the fight's tool hits the enemy, which flashes; looking
  around (`ls`, `cat`, `cd`…) is free; any other command, or a failed one, costs a heart and your pet
  flashes red. At 0 hearts you're knocked out and the threat comes back later.
- The adventure no longer crashes when the Sage Owl comes to teach you.

## v0.2.1 — 2026-09-22

- `bashou learn` takes a command apart and explains each piece: the command, every option, the
  arguments, pipes and redirections. With no command, it explains the last one your pet suggested.
- The prompt starts below your pet, at startup and after `clear`, so the first commands' output
  no longer hides under it.
- `bashou update` shows what's new from this changelog, and `bashou update --version v0.2.0`
  installs a given release, older ones too.
- Pets switch to new sprites and translations right after an update.
- Achievements that need a tool stay hidden in tests on machines that have it (fixes the first
  0.2.0 release run).
- In French, the Star line starts as "Poussière", which fits the pet board.

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
- Translating with an AI agent: `doc/agents/translation.md` tells it how to work with a native speaker.

## v0.1.0 — 2026-09-22

First release: a pet that lives next to your prompt and grows as you learn bash. Starters, pets
unlocked by commands and tools, achievements, fights in a sandbox, security challenges, an adventure
with bosses and questions, and updates from GitHub releases.
