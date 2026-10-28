# Bashou

**English** · [Français](README.fr.md)

[![CI](https://github.com/IAmAStealer/Bashou/actions/workflows/ci.yml/badge.svg)](https://github.com/IAmAStealer/Bashou/actions/workflows/ci.yml)
[![CodeQL](https://github.com/IAmAStealer/Bashou/actions/workflows/codeql.yml/badge.svg)](https://github.com/IAmAStealer/Bashou/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/IAmAStealer/Bashou/badge)](https://scorecard.dev/viewer/?uri=github.com/IAmAStealer/Bashou)
[![Release](https://img.shields.io/github/v/release/IAmAStealer/Bashou)](https://github.com/IAmAStealer/Bashou/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**A pixel-art pet in the corner of your terminal that grows while you learn the command line.**
Free, offline, no account, no AI.

| A pet that gives tips, and `bashou learn` | Fights in a sandbox shell |
|---|---|
| ![A small pixel-art stardust in the corner of the terminal, with a tip in its speech bubble, above a `bashou learn` explanation of a tar command](doc/img/prompt.svg) | ![bashou fight: a Planet and its hearts face the Log Hydra, the task in a bubble, and the arena shell below](doc/img/duel.svg) |
| **Pets to find** | **A banner to share** |
| ![The three starters, Stardust, Seedling and Pebble, then three of the first pets you can meet: a Droplet after 10 commands, a Mouseling after 10 programs, a Spore after 5 scripts](doc/img/pets.svg) | ![A Bashou banner: IAmAStealer's Satellite, level 12, the ten forms of the Packet family from Bit to Constellation, 58 achievements, 14 pets, 23 fights won, 17 lessons read, the skills Bash, Linux and Network, and the starter, a Moon](doc/img/share.png) |

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
No pet on Debian or Ubuntu? Run `bashou on` once: it adds one line to your `~/.bashrc` (to your `~/.zshrc` if you type it in zsh).
Updates come with `apt upgrade` or `dnf upgrade`.

**macOS**, **any other Linux**, zsh only, or git to follow the code as it's written: see [INSTALL.md](INSTALL.md).

## What you can do

Start with bash. Then pick what you want: Linux, packages, gpg and pass, SQL, CI/CD, Python, C or Rust.
Bashou runs in your real terminal, while you work: one pet for all your terminals, and it never draws over your text.

| Command | What it does |
|---|---|
| `bashou learn <command>` | Takes a command apart and explains every piece: options, arguments, pipes, redirections (88 commands, from `ls` to `tar`, `awk`, `gpg` and `kubectl`) |
| *(your pet)* | Gives tips as you go (Ctrl+R, `cd -`, `du -sh *`…) and notices the tools you haven't tried yet |
| *(achievements)* | **304 achievements** reward real skills: a pipe of 3 commands, `find -exec`, `sed -i`, `git bisect`… |
| `bashou fight` | Threats show up now and then: beat them in a sandbox shell with the right tool, `grep` against the Log Hydra, `awk` against the Ledger Golem |
| `bashou lesson` | The Sage Owl's library: lessons with drawings that grow page by page, on a path that opens as you pass |
| `bashou project` | 13 real projects in Python, Shell, C and Rust (merge PDFs, sort photos, a backup script…), one small step at a time |
| `bashou spot` | Quick game: an IPv6, a hash, base64, a JWT… say what it is, faster and faster |
| `bashou arena` | A timed fight, or a security investigation (a hidden file, a cron backdoor, a SUID binary) |
| `bashou adventure` | A walk through 13 topics with 477 questions about what goes wrong and what to check first, bosses and chests |
| `bashou share` | A QR code: your phone draws a banner of your pet and your progress, to send anywhere |

<details>
<summary><b>More about fights</b></summary>

They start with the first steps (an option to find in `--help`, a typo to fix in your editor, files to
tidy) and go up to Linux rights, services and git merge conflicts. A successful command with the right
tool hits the enemy; other commands cost you a heart (looking around with `ls`, `cat` or `find`, or a
typo, never does; in a fight where you fix a file, only a failed try with the tool does).

- **Code fights** hand you a small broken Python, C or Rust file to fix (a missing `;`, a loop that never
  ends, a memory leak, a shell injection).
- **Script fights** hand you a bash script with a habit that's fine at the prompt and a bug in a script
  (`ls` output in a loop, a name starting with `-`, `local x=$(cmd)`, `echo` on data, a temp file left
  behind): your fix wins only when the script works again on Bashou's own tricky files.
- **Package fights** ask your own machine with `apt`, `dpkg` or `rpm`, or have you fix a repository file.
- **CI/CD fights** hand you a GitHub Actions or GitLab CI file to fix (indentation, stages, a token in
  clear, `needs:` and `if:`, `when: manual`).
- **SQL fights** hand you an SQLite database to query and fix (`SELECT`, `JOIN`, `NULL`, `CREATE TABLE`,
  `INSERT … ON CONFLICT DO UPDATE`).
- **Secrets fights** teach `gpg` and `pass` with their own practice key and store: yours are never touched.
- **Network fights** read your addresses and routes with `ip`, find a listener with `ss`, compare `getent`
  and DNS, and read saved captures with `tcpdump -r`; nothing leaves your machine.

Beaten fights come back after 1, 7 and 30 days (spaced repetition), so what you learned stays.
In a fight, `lesson` opens the lesson that explains it.

</details>

## Pets

Choose a starter: Stardust, Seedling or Pebble. It grows up to level 20 and changes shape along the
way. 32 more pets hide in your terminal, each one from what it stands for: a Droplet after your first
10 commands, a night coder for your first programs, a mushroom for your own scripts, a chameleon for
sharp eyes… The swap board shows only their silhouette until you meet them.

**`bashou share`** lists exactly what the banner holds before the QR code: no commands, files, machine
names or dates. The progress travels inside the link, after the `#`, a part browsers never send to a
server. The first time, it asks for a nickname (`bashou share --name Nova` changes it).

## What's new

**0.11.0**
- **Your path in the library**: the lessons to take next come first (`f` shows them all), and hard
  lessons wait until you master the ones before.
- systemd is part of Linux, and the Snail family is redrawn as a slug building its shell.

**0.10.6**
- **Certificates**: six lessons and ten fights, from reading a certificate to running your own CA and
  revoking one, and a new pet, the Seal, that grows with them.
- SQL lessons and questions corrected and checked statement by statement.

**0.10.5**
- **Bash scripts** are a skill of their own, with eight fights that run your fixed script on hostile files.

**0.10.4**
- Fled a fight? Your pet stops reminding you of it; the threat still waits for `bashou fight` until midnight.
- Gary has his real colors: yellow-green eyes with red pupils and a green belly.

**0.10.3**
- **Threats wait all day**: a fight now waits until midnight and your pet repeats its warning every half
  hour, so you don't miss it. Experienced players get up to 2 threats a day.
- Homebrew installs run on Homebrew's own Python 3.15.

Every change, release by release: [CHANGELOG.md](CHANGELOG.md).

## Play on two computers

**`bashou export`** writes your progress in a small text file, `bashou-save-DATE.txt`, in the folder you
are in. Carry it to the other computer the way you like (a mail to yourself, an attachment, a chat), then
run **`bashou import bashou-save-DATE.txt`** there, or `bashou import` alone and paste the text. Nothing
is lost: for each thing, Bashou keeps the best of the two computers.

By default the file holds only your achievements, pets, lessons, fights and adventure: no command, no
tool count, no date. `bashou export --full` carries everything, counters included. Both computers need
the same version of Bashou.

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
`source /usr/share/bashou/bashou.bash` line from `~/.bashrc` (and the `bashou.zsh` one from `~/.zshrc`).

Installed with git or Homebrew: see [INSTALL.md](INSTALL.md#uninstall).

Your progress stays in `~/.local/share/bashou` (delete it too to forget everything).

## More

The [guide](doc/GUIDE.md) explains pets, achievements, fights and translations.
Something broken, or an idea? [Report a bug](https://github.com/IAmAStealer/Bashou/issues/new?template=1-bug.yml)
or [suggest an idea](https://github.com/IAmAStealer/Bashou/issues/new?template=2-idea.yml).
Want to help? Pixel art, lessons, security challenges and adventure questions are welcome: [contributing](.github/CONTRIBUTING.md).
[How it started](doc/STORY.md): made with AI for responsible use (learning, so you can do it too); the Rust version is written by hand.

MIT license.
