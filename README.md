# Bashou

A little pixel-art pet that lives in the corner of your terminal and grows while you learn bash.
Run commands, try new tools, and collect new pets along the way.

![A small pixel-art stardust in the corner of the terminal, with a tip in its speech bubble, above
a `bashou learn` explanation of a tar command](doc/img/prompt.svg)

## Learn bash without asking an AI

Bashou teaches in your real terminal, while you work. It runs offline: no account, no AI model, no
tokens spent to learn what a command does.

- **`bashou learn <command>`** takes a command apart and explains every piece: the command, each
  option, the arguments, pipes and redirections (55 commands, from `ls` to `tar`, `awk` and `kubectl`).
  With no command, it explains the last one your pet suggested.
- **Your pet gives tips** as you go (Ctrl+R, `cd -`, `du -sh *`…) and notices the tools you haven't
  tried yet.
- **99 achievements** reward real skills: a pipe of 3 commands, `find -exec`, `sed -i`, `git bisect`,
  `tar -tf`…
- **Threats** show up now and then. `bashou fight` opens a sandbox shell where you beat them with the
  right tool: `grep` against the Log Hydra, `awk` against the Ledger Golem. A successful command with
  the right tool hits the enemy; other commands cost you a heart. Code fights hand you a small broken
  Python or C file to fix (a missing `;`, a loop that never ends, a memory leak, a shell injection);
  package fights ask your own machine with `apt`, `dpkg` or `rpm`, or have you fix a repository file.
  Beaten fights come back after 1, 7 and 30 days (spaced repetition), so what you learned stays.
- **`bashou explain python list`** (or `dict`, `loop`, `recursion`; `bashou explain c malloc`…): a
  short note with an example, for the code fights.
- **`bashou security`**: small investigations (a hidden file, a cron backdoor, a SUID binary).
- **`bashou adventure`**: a walk through 10 topics (coding logic, bash, Linux, systemd, Python, Rust,
  C, Debian, Rocky Linux, CI/CD) with 240 questions about what goes wrong and what to check first, bosses, and
  chests that open with real commands.

![bashou fight: a Planet and its hearts face the Log Hydra, the task in a bubble, and the arena
shell below](doc/img/duel.svg)

## Discover pets

Choose a starter: Stardust, Seedling or Pebble. It grows up to level 20 and changes shape along the
way. What it becomes is for you to find out.

25 more pets hide in your terminal. Each one comes from what it stands for: a Droplet after your
first 10 commands (it keeps changing shape as you type), a night coder for your first programs, a
mushroom for your own scripts, others for a new tool used often enough, a long pipe, a fight lost or
won, a walk in the adventure… The swap board shows only their silhouette until you meet them.

![The three starters, Stardust, Seedling and Pebble, then three of the first pets you can meet: a
Droplet after 10 commands, a Mouseling after 10 programs, a Spore after 5 scripts](doc/img/pets.svg)

## Install

Copy this line into your terminal:

```bash
git clone https://github.com/IAmAStealer/Bashou.git ~/.bashou && echo 'source ~/.bashou/bashou.bash' >> ~/.bashrc && source ~/.bashrc
```

You need bash and python3 (already there on most Linux systems).

## Use

```bash
bashou          # see how your pet is doing
bashou -h       # all commands
bashou update   # get the new version (your pet tells you when there is one)
```

## Uninstall

```bash
sed -i '/\.bashou\/bashou\.bash/d' ~/.bashrc && rm -rf ~/.bashou
```

Your progress stays in `~/.local/share/bashou` (delete it too to forget everything).

## More

The [guide](doc/GUIDE.md) explains pets, achievements, fights and translations.
Want to help? Pixel art, security challenges and adventure questions are welcome: [contributing](.github/CONTRIBUTING.md).
[How it started](doc/STORY.md): made with AI for responsible use (learning, so you can do it too); the Rust version is written by hand.

MIT license.
