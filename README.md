# Bashou

A pixel-art pet that lives in the top-right corner of your terminal and grows as you learn bash.

- It breathes, blinks and looks around while you're at the prompt, and falls asleep when the terminal
  has been idle for 5–15 minutes.
  It's erased before each command, so it never ends up in your scrollback.
- **Every command counts.** Milestones (50, 200, 500… commands) unlock new pets.
- **New tools unlock pets too.** Use `find`, `awk`, `grep`, `sed`, `ps`, `xargs`, `jq` or `strace`
  and a matching creature joins you.
- **Achievements evolve your pets.** Each pet has a family of achievements (`find -exec`,
  `awk -F`, `sort -rn`, a heredoc…): 2 of them evolve it, all of them make it legendary.
  Evolved pets learn new actions: washing, humming, tail flicks, then dancing and sparkles.
- **Pick your pet** on a 4×4 board with `bashou swap`.
- **Pets talk.** Every 10–20 minutes your pet gives a tip for its tool, a hint toward your next
  achievement (with an example command), or a line shaped by your achievements (win fights and it
  gets bolder). `bashou talk` asks it right away.
- **Threats.** A few times a day a threat shows up (« ⚠ A Log Hydra is coming! Use `grep` to fight
  it »). `bashou fight` drops you in a sandbox bash with random data: solve the task with the named
  tool, `answer` it, and the threat's pet joins you. `hint` helps, `flee` runs away. See [PLAN.md](PLAN.md).

## Install

Requires bash 4.4+, Python 3.9+, and a terminal with 24-bit color.

```bash
git clone <repo> ~/Bashou
echo 'source ~/Bashou/bashou.bash' >> ~/.bashrc
```

## Commands

```bash
bashou level            # commands run, next unlock
bashou pets             # your collection
bashou achievements     # what you earned, and what to try next
bashou fight            # enter the arena (any time, or when a threat shows up)
bashou talk             # your pet says something useful
bashou swap             # board to pick your pet (or: bashou swap fox)
bashou off / on         # hide / show the pet
bashou stats            # commands, top tools, constructs, streaks
```

Tab completion works for commands, pet names and `dev` arguments.

## Privacy

Bashou reads each new history entry to count tools and constructs, then throws it away.
Only counters are kept, in `~/.local/share/bashou/state.json`.

## Tests

```bash
python3 -m unittest            # ~25 s; tests/test_shell.py drives a real bash on a pty
```

## License

MIT
