# Bashou guide

A pixel-art pet that lives in the top-right corner of your terminal and grows as you learn bash.

- It breathes, blinks and looks around while you're at the prompt, and falls asleep when the terminal
  has been idle for 5–15 minutes.
  It's erased before each command, so it never ends up in your scrollback.
- **Choose a starter** the first time: Stardust, Seedling or Pebble. It levels up every 5 achievements
  (up to level 20) and changes shape along the way; what it becomes is a surprise (the swap board
  tells the level of the next form). A form once reached is never lost. Only `bashou reset` lets you
  choose again.
- **Every command counts.** Milestones (10, 50, 200, 500… commands) unlock new pets.
- **New tools unlock pets too.** Use `find`, `awk`, `grep`, `sed`, `ps`, `xargs`, `jq` or `strace`
  and a matching creature joins you.
- **Achievements evolve your pets.** Each pet has a family of achievements (`find -exec`,
  `awk -F`, `sort -rn`, a heredoc…): 2 of them evolve it, all of them make it legendary.
  Evolved pets learn new actions: washing, humming, tail flicks, then dancing and sparkles.
  The pet tells you when it's evolving; watch it with `bashou evolve` (it keeps its old look until
  then). In `bashou swap`, `f` switches between the forms it has reached, and it keeps its actions.
- **Pipes.** Chain 3 commands with `|` ten times, or beat the Knot Eel in the arena, and the
  Octopus joins you.
- **Safety.** Your pet warns you right away about risky commands: a download piped into a shell
  (`curl … | sh`), `chmod 777`, skipped HTTPS checks (`curl -k`), `rm -r` on `/` or `~`,
  `StrictHostKeyChecking=no`, `sudo pip install`, `sshpass -p`. Five of them attract the **Gremlin**,
  which evolves as you pick up safe habits (reading a script before running it, checksums, `chmod u+x`)
  and ends up an Orc.
- **Security challenges.** `bashou security` lists small investigations, easy to hard: a hidden
  file, an encoded note, brute-force attempts in an `auth.log`, a defaced website, a cron backdoor, a
  SUID program. Each one runs in a sandbox folder with fake, harmless data. Solving them evolves the
  Gremlin into an Orc.
- **Adventure.** `bashou adventure`: your starter walks into the world, seen from behind, through
  meadows, hills, forests, deserts, lakes and dungeons. The road splits into topics (Bash, Linux,
  Python, Rust, C, Debian, Rocky Linux, CI/CD): monsters ask a question (wrong: ♥ -1), locked chests
  open with a real shell trick in a sandbox (`mkdir -p`, `mv`, `chmod`, `tar`…) and may give a heart
  back, and each path ends with a boss: timed questions (20 s each), each miss costs a heart. Beat it
  and it's a checkpoint, the topic levels up (harder questions next time). Lose your last heart and
  you go back to the last checkpoint, where you can pick another path. Finish a chapter and a new quest starts. `s` saves and quits at any time.
  Finishing chapter 1 brings the Snail (a slug at first), and its achievements follow your adventure.
- **Typos.** On `command not found` your pet laughs kindly and suggests the command you meant.
- **Pick your pet** on the board with `bashou swap`.
- **Pets talk.** Every 10–20 minutes your pet gives a tip for its tool, a hint toward your next
  achievement (with an example command), or a line shaped by your achievements (win fights and it
  gets bolder). `bashou talk` asks it right away.
- **Threats.** A few times a day your pet warns you that a threat is coming (« ⚠ A Log Hydra is coming! Use `grep` to fight
  it »). `bashou fight` drops you in a sandbox bash with random data: solve the task with the named
  tool, `answer` it, and the threat's pet joins you. `hint` helps, `flee` runs away. No threat, no
  fight: the arena only opens after your pet's warning. Code fights hand you a small broken Python
  or C file instead: its first lines say what goes in, what should come out and how to run it; fix
  it and `answer done`. Opening an editor is free.

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
bashou learn            # takes its last suggested command apart; or: bashou learn tar -czf a.tgz d
bashou explain          # a short note on a code topic: bashou explain python list, bashou explain c malloc
bashou evolve           # watch your pets evolve (s skips)
bashou swap             # board to pick your pet (or: bashou swap fox); f switches its form
bashou off / on         # hide / show the pet
bashou stats            # commands, top tools, constructs, streaks
bashou config           # list settings (see Configuration)
bashou version          # which version this is (and if a newer one is out)
bashou update           # get the new version from GitHub (--version v0.2.0: a given one, older too)
bashou security         # security challenges (bashou security 3 starts the third)
bashou adventure        # walk into the world with your starter (s: save & quit)
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
bashou config talk 30           # a line every 30 minutes, in a pause
bashou config talk off          # never talks on its own (achievements and threats still show)
bashou config quiet 120         # and only after 2 minutes without typing
```

| Setting | Default | What it does |
|---|---|---|
| `bubble` | `5-10` | How many commands a speech bubble (tips, hints, achievements) stays on screen. When another message is waiting, the current one closes after 2 commands. |
| `size` | `small` | `large` shows big pixel art for the pets that have some (for now the Tarantula), when the terminal is wide enough. |
| `talk` | `10-20` | Minutes between the things your pet says on its own (tips, hints, invitations). `off` keeps it quiet; what you earn (achievements, evolutions, threats, `command not found`) still shows. |
| `quiet` | `60` | Seconds without a command or a keypress before it says one: it waits for a pause instead of cutting into your work. |
| `updates` | `on` | Once a day, your pet looks for a new release on GitHub (a `git fetch` of the install folder, nothing about you is sent) and tells you in a bubble. `bashou update` installs it; running pets switch to it by themselves. |

Settings are saved in `~/.local/share/bashou/state.json` (only the ones you changed) and apply to
every terminal right away. `bashou reset` keeps your language but resets settings. The language is
chosen with `bashou language`.

## Releases and security checks

Every push runs the tests (Python 3.9 and 3.13) and the security checks:

- **Standard library only**: a test fails on any third-party import, network module, `eval`/`exec`,
  `pickle`, `os.system` or `shell=True`. Nothing to `pip install`, so no dependency to trust.
- **Bandit** (Python security linter), **ShellCheck** (the bash loader), **Gitleaks** (secrets in
  the whole history), **CodeQL** (GitHub code scanning, also weekly).
- The GitHub Actions are pinned to a commit, and Dependabot proposes their updates.

To release, first add a `## v1.2.3 — YYYY-MM-DD` section to `CHANGELOG.md` (written for players:
it becomes the release notes), then push a commit to `main` whose message has a line
`release: v1.2.3`. Once the tests and security checks pass, CI creates the `v1.2.3` tag and the
GitHub release; without a changelog section it stops before tagging (*Actions → Release → Run
workflow* does the same by hand). Pets only offer these tags, never a plain commit on `main`.

## Contributing

Pixel art, security challenges and adventure questions are welcome as pull requests: see
[pixel art](contributing/pixel-art.md), [security challenges](contributing/security-challenges.md) and
[adventure questions](contributing/questions.md).

## Privacy

Bashou reads each new history entry to count tools and constructs, then throws it away.
Only counters are kept, in `~/.local/share/bashou/state.json`.

## Translations

English is the source language. Translations live in `bashou/locales/<lang>.json`, keyed by the
English text; an empty value falls back to English, so a language can ship half-done. Adventure
questions are translated in `bashou/adventure/questions/<lang>/`. Only JSON files, no code: see
[translations.md](contributing/translations.md).

```bash
python3 -m bashou.i18n         # add new messages (empty) to every catalog, show progress
```

To add a language, create `bashou/locales/<lang>.json` with `{"@language": "Deutsch"}` and run the
command above.

## Tests

```bash
python3 -m unittest            # ~45 s; tests/test_shell.py drives a real bash on a pty
```

## License

MIT
