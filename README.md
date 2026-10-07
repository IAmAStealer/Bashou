# Bashou

**English** · [Français](README.fr.md)

[![CI](https://github.com/IAmAStealer/Bashou/actions/workflows/ci.yml/badge.svg)](https://github.com/IAmAStealer/Bashou/actions/workflows/ci.yml)
[![CodeQL](https://github.com/IAmAStealer/Bashou/actions/workflows/codeql.yml/badge.svg)](https://github.com/IAmAStealer/Bashou/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/IAmAStealer/Bashou/badge)](https://scorecard.dev/viewer/?uri=github.com/IAmAStealer/Bashou)
[![Release](https://img.shields.io/github/v/release/IAmAStealer/Bashou)](https://github.com/IAmAStealer/Bashou/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Learn Linux commands and bash scripting for free, in your own terminal.

A little pixel-art pet lives in the corner of your terminal. It grows while you learn the command line.
Start with bash. Then pick what you want: Linux, systemd, packages, gpg and pass, SQL, CI/CD, Python, C or Rust.
Run commands, try new tools, and collect new pets along the way.

![A small pixel-art stardust in the corner of the terminal, with a tip in its speech bubble, above
a `bashou learn` explanation of a tar command](doc/img/prompt.svg)

## Install

Bashou has its own signed repositories: install it once, and it updates with the rest of your system.

**Debian, Ubuntu** (apt):

```bash
sudo mkdir -p -m 755 /etc/apt/keyrings
sudo curl -fsSLo /etc/apt/keyrings/bashou.asc https://iamastealer.github.io/Bashou/bashou.asc
printf '%s\n' 'Types: deb' 'URIs: https://iamastealer.github.io/Bashou/deb/' 'Suites: ./' \
  'Signed-By: /etc/apt/keyrings/bashou.asc' | sudo tee /etc/apt/sources.list.d/bashou.sources
sudo apt update && sudo apt install bashou
```

**Rocky, Alma, RHEL, Fedora** (dnf):

```bash
sudo curl -fsSLo /etc/yum.repos.d/bashou.repo https://iamastealer.github.io/Bashou/bashou.repo
sudo dnf install bashou
```

Open a new terminal: your pet is there. Every user gets one, except root.
`bashou off` hides it, in new terminals too. `bashou on` brings it back.
No pet on Debian or Ubuntu? Run `bashou on` once: it adds one line to your `~/.bashrc`.
Updates come with `apt upgrade` or `dnf upgrade`.

**Any other Linux**, or to follow the code as it's written, with git:

```bash
git clone https://github.com/IAmAStealer/Bashou.git ~/.bashou && echo 'source ~/.bashou/bashou.bash' >> ~/.bashrc && source ~/.bashrc
```

You need bash and python3. Most Linux systems already have them.
Installed with git on Debian or Red Hat, and want the repository instead? Run `bashou update --packages`.
It shows every command it will run, asks you, then moves you over. Your pets and progress are kept.

## What's new

**0.8.3**
- **Bashou speaks French** on the web: a French README, a French home page, and French forms to report a
  bug or suggest an idea.
- **On right after installing**: with `apt` or `dnf`, open a new terminal and your pet is there.
  `bashou off` keeps it off until `bashou on`.
- The Squab has a new look.

**0.8.2**
- **Your starter grows further**: four new forms for each line, up to the Universe, the World tree and a Pet rock.
- **`bashou spot`**: password hashes, CSRF tokens and OAuth2 strings to recognise.
- A second secret pet, for players who like a good fight.

**0.8.1**
- **`bashou share`**: your card now shows your best `bashou spot` score and your rare pets: the ones you
  grew to their last form, and the hardest to meet.

**0.8.0**
- **`bashou project`**: 13 real projects to build in Python, Shell, C or Rust, one small step at a time,
  and a new pet, the Landscape, that grows from a hill into a town as you finish them.
- **`bashou spot`**: an IPv6, a hash, base64, a JWT, a line of Rust? Say what the string is, as fast as
  you can, in 25 seconds. A new pet comes with it: the Chameleon, up to the Eagle.
- **`bashou here`** brings your pet to the terminal you're typing in.
- A new lesson on command substitution, `$( )`: quotes, exit codes, and passwords from `pass` in scripts.

**0.7.0**
- The Sage Owl's library is a path now: each lesson opens once you've passed the ones before it, and
  the owl warms you up with two questions on what you'll build on.
- New lessons for the first steps (`--help` and `man`, nano or vi, a first taste of regex) and for logic.
- 21 new fights: reading `--help`, fixing a typo in your editor, tidying files, wildcards, `nproc`, `if`
  and `&&`, stderr, quotes, a broken shebang, a `for` loop, `grep -E`, groups, rights, `du`, `tar`, a
  service file, `curl -I`, and git commits, branches and merge conflicts.
- One pet for all your terminals: the others still count your commands.

Every change, release by release: [CHANGELOG.md](CHANGELOG.md).

## Learn the terminal without asking an AI

Bashou teaches in your real terminal, while you work. It runs offline: no account, no AI model, no
tokens spent to learn what a command does. It stays out of your way: one pet for all your terminals, and
it never draws over your text.

- **`bashou learn <command>`** takes a command apart and explains every piece: the command, each
  option, the arguments, pipes and redirections (71 commands, from `ls` to `tar`, `awk`, `gpg` and `kubectl`).
  With no command, it explains the last one your pet suggested.
- **Your pet gives tips** as you go (Ctrl+R, `cd -`, `du -sh *`…) and notices the tools you haven't
  tried yet.
- **171 achievements** reward real skills: a pipe of 3 commands, `find -exec`, `sed -i`, `git bisect`,
  `tar -tf`…
- **Threats** show up now and then. `bashou fight` opens a sandbox shell where you beat them with the
  right tool: `grep` against the Log Hydra, `awk` against the Ledger Golem. They start with the first
  steps (an option to find in `--help`, a typo to fix in your editor, files to tidy) and go up to Linux
  rights, services and git merge conflicts. A successful command with
  the right tool hits the enemy; other commands cost you a heart. Code fights hand you a small broken
  Python or C file to fix (a missing `;`, a loop that never ends, a memory leak, a shell injection);
  package fights ask your own machine with `apt`, `dpkg` or `rpm`, or have you fix a repository file;
  CI/CD fights hand you a GitHub Actions or GitLab CI file to fix (indentation, stages, a token in
  clear, `needs:` and `if:`, `when: manual`); SQL fights hand you an SQLite database to query and fix
  (`SELECT`, `JOIN`, `CREATE TABLE`, `INSERT`, `UPDATE`, `INSERT … ON CONFLICT DO UPDATE`).
  Secrets fights teach `gpg` and `pass`: lock and open a file, spot a forged download by its signature,
  take a password out of a script with `$(pass show …)`. They bring their own practice key and store:
  yours are never touched. Network fights read your own addresses and routes with `ip`, find a
  listener with `ss`, compare `getent` and DNS, and read saved captures with `tcpdump -r`; their
  servers listen on 127.0.0.1 only, and nothing leaves your machine.
  Beaten fights come back after 1, 7 and 30 days (spaced repetition), so what you learned stays.
- **`bashou lesson`**: the Sage Owl's library. Lessons with drawings that grow page by page (the stack
  and the heap, where output goes, permissions, `$( )`…), on a path: each one opens once you've passed the
  ones before it, by winning a fight or earning an achievement, and prepares your next step. Your editor
  is yours to pick, nano or vi. In a fight, `lesson` opens the one that explains it.
- **`bashou project`**: you want to practise a language but don't know *what* to program? 13 real
  projects in Python, Shell, C and Rust, from very easy to hard: merge PDFs, sort your photos by date, a
  backup script, a Pomodoro timer, an internet outage logger… One small step at a time: each step says what
  to do and when it's done, never how, with a hint if you're stuck and a short explanation once it's done.
- **`bashou spot`**: a quick game. A string shows up: an IPv6 address, a MAC, a hash, base64, a JWT, a
  Linux password hash, a CSRF token, OAuth2, a date, a regex, a line of Python or SQL… Say what it is with the arrow keys, faster and faster, in 25
  seconds. The ones you'll meet in logs and configs, recognised at a glance.
- **`bashou arena`**: come and fight when you want. A timed fight (hearts and a clock), or a security
  investigation with no clock (a hidden file, a cron backdoor, a SUID binary). Lose, and the arena
  closes for an hour.
- **`bashou adventure`**: a walk through 12 topics (coding logic, bash, Linux, systemd, Python, Rust,
  C, Debian, Rocky Linux, CI/CD, SQL, networks) with 379 questions about what goes wrong and what to check first, bosses, and
  chests that open with real commands.

![bashou fight: a Planet and its hearts face the Log Hydra, the task in a bubble, and the arena
shell below](doc/img/duel.svg)

## Discover pets

Choose a starter: Stardust, Seedling or Pebble. It grows up to level 20 and changes shape along the
way. What it becomes is for you to find out.

31 more pets hide in your terminal. Each one comes from what it stands for: a Droplet after your
first 10 commands (it keeps changing shape as you type), a night coder for your first programs, a
mushroom for your own scripts, others for a new tool used often enough, a long pipe, a fight lost or
won, a walk in the adventure, a landscape that grows with your projects, a chameleon for sharp eyes… The swap board shows only their silhouette until you meet them.

![The three starters, Stardust, Seedling and Pebble, then three of the first pets you can meet: a
Droplet after 10 commands, a Mouseling after 10 programs, a Spore after 5 scripts](doc/img/pets.svg)

## Show off your pet

Proud of how far you got? **`bashou share`** shows a QR code in your terminal. Scan it, and your phone
draws a banner of your pet, its family and your progress (with your best `bashou spot` score and a row
of your rare pets), with a button to send it on Signal, WhatsApp
or anywhere you like. The first time, it asks for a nickname to show instead of your real name
(`bashou share --name Nova` changes it).

![A Bashou banner: IAmAStealer's Satellite, level 12, the ten forms of the Packet family from Bit to
Constellation, 58 achievements, 14 pets, 23 fights won, 17 lessons read, the skills Bash, Linux
and Network, and the starter, a Moon](doc/img/share.png)

Before the QR code, Bashou lists exactly what the card holds: no commands, files, machine names or
dates. The progress travels inside the link, after the `#`, a part browsers never send to a server:
the page draws the banner on your phone and keeps nothing.

## Your data stays on your machine

Bashou collects nothing. No account, no telemetry, no analytics, no ads: **you are not the product.**
It reads your commands only to count tools and constructs, keeps those counters in
`~/.local/share/bashou`, and never sends them anywhere. The only thing it asks the internet is whether
a new version is out (once a day; `bashou config updates off` stops it, and apt or dnf installs leave it
to your package manager).

Bashou is a small side project, made with spare AI tokens by someone who likes teaching and helping
people. There is nothing to sell.

## Use

```bash
bashou          # see how your pet is doing
bashou -h       # all commands
bashou here     # bring your pet to this terminal
bashou update   # get the new version (your pet tells you when there is one; apt or dnf for packages)
```

## Uninstall

Installed as a package: `sudo apt remove bashou` or `sudo dnf remove bashou`, then remove the
`source /usr/share/bashou/bashou.bash` line from `~/.bashrc`.

Installed with git:

```bash
sed -i '/\.bashou\/bashou\.bash/d' ~/.bashrc && rm -rf ~/.bashou
```

Your progress stays in `~/.local/share/bashou` (delete it too to forget everything).

## More

The [guide](doc/GUIDE.md) explains pets, achievements, fights and translations.
Something broken, or an idea? [Report a bug](https://github.com/IAmAStealer/Bashou/issues/new?template=1-bug.yml)
or [suggest an idea](https://github.com/IAmAStealer/Bashou/issues/new?template=2-idea.yml).
Want to help? Pixel art, lessons, security challenges and adventure questions are welcome: [contributing](.github/CONTRIBUTING.md).
[How it started](doc/STORY.md): made with AI for responsible use (learning, so you can do it too); the Rust version is written by hand.

MIT license.
