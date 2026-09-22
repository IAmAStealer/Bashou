# Bashou

A little pixel-art pet that lives in the corner of your terminal and grows while you learn bash.
Run commands, try new tools, and collect new pets along the way.

![A pixel-art planet in the corner of the terminal, with a tip in its speech bubble, above a
`bashou learn` explanation of a tar command](doc/img/prompt.svg)

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
  the right tool hits the enemy; other commands cost you a heart.
- **`bashou security`**: small investigations (a hidden file, a cron backdoor, a SUID binary).
- **`bashou adventure`**: a walk through 8 topics (bash, Linux, Python, Rust, C, Debian, Rocky Linux,
  CI/CD) with 166 questions, bosses, and chests that open with real commands.

![bashou fight: your pet and its hearts face the Log Hydra, the task in a bubble, and the arena
shell below](doc/img/duel.svg)

## Collect pets

25 pets, each with 3 forms, unlocked by what you do: 10 uses of `find` bring the Fox, `awk` the Owl,
`git` the Beaver. Your starter (Stardust, Seedling or Pebble) grows up to level 20 and keeps changing
shape.

![Twelve of the pets: Stardust, Comet, Planet, Star, Fox, Kitsune, Octopus, Kraken, Owl, Dragon,
Axolotl, Ghost](doc/img/pets.svg)

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
