# Bashou guide

A pixel-art pet that lives in the top-right corner of your terminal and grows as you learn bash.

- It breathes, blinks and looks around while you're at the prompt, and falls asleep when the terminal
  has been idle for 5–15 minutes.
  It's erased before each command, so it never ends up in your scrollback.
- **Choose a starter** the first time: Kitten, Seedling or Pebble. It levels up every 5 achievements
  (up to level 9) and changes shape at levels 4 and 7: Kitten → Cat → Lion, Seedling → Sprout →
  Tree spirit, Pebble → Rock golem → Crystal golem. Only `bashou reset` lets you choose again.
- **Every command counts.** Milestones (10, 50, 200, 500… commands) unlock new pets.
- **New tools unlock pets too.** Use `find`, `awk`, `grep`, `sed`, `ps`, `xargs`, `jq` or `strace`
  and a matching creature joins you.
- **Achievements evolve your pets.** Each pet has a family of achievements (`find -exec`,
  `awk -F`, `sort -rn`, a heredoc…): 2 of them evolve it, all of them make it legendary.
  Evolved pets learn new actions: washing, humming, tail flicks, then dancing and sparkles.
- **Pick your pet** on a 4×4 board with `bashou swap`.
- **Pets talk.** Every 10–20 minutes your pet gives a tip for its tool, a hint toward your next
  achievement (with an example command), or a line shaped by your achievements (win fights and it
  gets bolder). `bashou talk` asks it right away.
- **Threats.** A few times a day your pet warns you that a threat is coming (« ⚠ A Log Hydra is coming! Use `grep` to fight
  it »). `bashou fight` drops you in a sandbox bash with random data: solve the task with the named
  tool, `answer` it, and the threat's pet joins you. `hint` helps, `flee` runs away. No threat, no
  fight: the arena only opens after your pet's warning.

## Install

Requires bash 4.4+, Python 3.9+, and a terminal with 24-bit color. See the one-line install in the
[README](../README.md).

## Commands

```bash
bashou start            # choose your starter (first launch does it for you)
bashou language         # choose the language (asked once at first launch)
bashou level            # starter level, commands run, next unlock
bashou pets             # your collection
bashou achievements     # what you earned, and what to try next
bashou fight            # enter the arena, once your pet has announced a threat
bashou talk             # your pet says something useful
bashou swap             # board to pick your pet (or: bashou swap fox)
bashou off / on         # hide / show the pet
bashou stats            # commands, top tools, constructs, streaks
bashou config           # list settings (see Configuration)
bashou reset            # start over with a new starter (asks first, keeps a backup)
```

Tab completion works for commands, pet names and `dev` arguments.

## Configuration

`bashou config` lists the settings with their current value and default.

```bash
bashou config                   # list all settings
bashou config bubble            # show one
bashou config bubble 3-8        # a speech bubble stays for 3 to 8 commands (random in the range)
bashou config bubble 5          # always 5 commands
bashou config bubble default    # back to the default (5-10)
```

| Setting | Default | What it does |
|---|---|---|
| `bubble` | `5-10` | How many commands a speech bubble (tips, hints, achievements) stays on screen. When another message is waiting, the current one closes after 2 commands. |

Settings are saved in `~/.local/share/bashou/state.json` (only the ones you changed) and apply to
every terminal right away. `bashou reset` keeps your language but resets settings. The language is
chosen with `bashou language`.

## Privacy

Bashou reads each new history entry to count tools and constructs, then throws it away.
Only counters are kept, in `~/.local/share/bashou/state.json`.

## Translations

English is the source language. Translations live in `bashou/locales/<lang>.json`, keyed by the
English text; an empty value falls back to English, so a language can ship half-done.

```bash
python3 -m bashou.i18n         # add new messages (empty) to every catalog, show progress
```

Keep the `{placeholders}` as they are. To add a language, add it to `LANGUAGES` in `bashou/i18n.py`
and run the command above.

## Tests

```bash
python3 -m unittest            # ~45 s; tests/test_shell.py drives a real bash on a pty
```

## License

MIT
