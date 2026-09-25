# Bashou

A little pixel-art pet that lives in the corner of your terminal and grows while you learn the command
line: bash first, then Linux, systemd, packages, gpg and pass, SQL, CI/CD, Python, C and Rust, whichever
you pick. Run commands, try new tools, and collect new pets along the way.

![A small pixel-art stardust in the corner of the terminal, with a tip in its speech bubble, above
a `bashou learn` explanation of a tar command](doc/img/prompt.svg)

## Learn the terminal without asking an AI

Bashou teaches in your real terminal, while you work. It runs offline: no account, no AI model, no
tokens spent to learn what a command does.

- **`bashou learn <command>`** takes a command apart and explains every piece: the command, each
  option, the arguments, pipes and redirections (70 commands, from `ls` to `tar`, `awk`, `gpg` and `kubectl`).
  With no command, it explains the last one your pet suggested.
- **Your pet gives tips** as you go (Ctrl+R, `cd -`, `du -sh *`…) and notices the tools you haven't
  tried yet.
- **131 achievements** reward real skills: a pipe of 3 commands, `find -exec`, `sed -i`, `git bisect`,
  `tar -tf`…
- **Threats** show up now and then. `bashou fight` opens a sandbox shell where you beat them with the
  right tool: `grep` against the Log Hydra, `awk` against the Ledger Golem. A successful command with
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
- **`bashou explain python list`** (or `dict`, `loop`, `recursion`; `bashou explain c malloc`,
  `bashou explain network cidr`…): a short note with an example, for the code and network fights.
- **`bashou lesson`**: the Sage Owl's library. Lessons with drawings that grow page by page (the stack
  and the heap, where output goes, permissions…), unlocked as you play, each one preparing your next step.
- **`bashou security`**: small investigations (a hidden file, a cron backdoor, a SUID binary).
- **`bashou adventure`**: a walk through 12 topics (coding logic, bash, Linux, systemd, Python, Rust,
  C, Debian, Rocky Linux, CI/CD, SQL, networks) with 343 questions about what goes wrong and what to check first, bosses, and
  chests that open with real commands.

![bashou fight: a Planet and its hearts face the Log Hydra, the task in a bubble, and the arena
shell below](doc/img/duel.svg)

## Discover pets

Choose a starter: Stardust, Seedling or Pebble. It grows up to level 20 and changes shape along the
way. What it becomes is for you to find out.

29 more pets hide in your terminal. Each one comes from what it stands for: a Droplet after your
first 10 commands (it keeps changing shape as you type), a night coder for your first programs, a
mushroom for your own scripts, others for a new tool used often enough, a long pipe, a fight lost or
won, a walk in the adventure… The swap board shows only their silhouette until you meet them.

![The three starters, Stardust, Seedling and Pebble, then three of the first pets you can meet: a
Droplet after 10 commands, a Mouseling after 10 programs, a Spore after 5 scripts](doc/img/pets.svg)

## Show off your pet

Proud of how far you got? **`bashou share`** shows a QR code in your terminal. Scan it, and your phone
draws a banner of your pet, its family and your progress, with a button to send it on Signal, WhatsApp
or anywhere you like. Add a nickname with `bashou share --name Nova`.

![A Bashou banner: Alexis's Satellite, level 12, the ten forms of the Packet family from Bit to
Constellation, 58 achievements, 14 pets, 23 fights won, 17 lessons read, and the skills Bash, Linux
and Network](doc/img/share.png)

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

## Install

Bashou has its own signed repositories: install it once, and it updates with the rest of your system.

**Debian, Ubuntu** (apt):

```bash
sudo install -dm755 /etc/apt/keyrings
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

Then each user who wants a pet runs `bashou setup` (it adds one line to their `~/.bashrc`). Updates come
with `apt upgrade` or `dnf upgrade`.

**Any other Linux**, or to follow the code as it's written, with git:

```bash
git clone https://github.com/IAmAStealer/Bashou.git ~/.bashou && echo 'source ~/.bashou/bashou.bash' >> ~/.bashrc && source ~/.bashrc
```

You need bash and python3 (already there on most Linux systems). Installed with git on Debian or Red Hat
and want the repository instead? `bashou update --packages` shows every command it will run, asks, then
moves you over; your pets and progress are kept.

## Use

```bash
bashou          # see how your pet is doing
bashou -h       # all commands
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
