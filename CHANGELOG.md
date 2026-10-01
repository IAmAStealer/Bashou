# Changelog

Every release has a section here, written for players. CI refuses to tag a release without one
(`python3 tools/changelog.py v1.2.3` prints the section it will publish).

## v0.6.6 — 2026-09-29

- In a very small window, the commands that draw a screen (`bashou evolve`, `swap`, `lesson`,
  `adventure`, `start` and `share`) tell you the window is too small and the size they need, instead of
  drawing a broken screen that can look stuck. `bashou share` needs room for the whole QR code, or
  your phone can't scan it.
- In a narrow window, the progress bar of `bashou` is shorter, so it stays on one line.
- With several terminals open, your pet lives in only one of them, the first you opened, instead of
  one pet (and one background process) in each. The commands you type in the other terminals still
  count for it. When you close its terminal, the pet moves to the next terminal where you press Enter.
- The Sage Owl's library is now a path. Each lesson opens once you've passed the lessons that come
  before it: win one of their fights, earn one of their achievements, or earn enough achievements in
  all. Paths cross themes where one idea needs another: Python and C wait for shell scripts, loops and
  logic, and SQL waits for the text tools. Commands alone no longer open lessons. The lessons you
  already opened stay open, and a lesson from a skill you don't learn never blocks you.
- A new Logic lesson explains how a program decides: yes or no answers, `if`, `!` (not), `&&` (and)
  and `||` (or). Two new fights put it into practice: the Negation Gnome turns a party door's guard
  around, and the Coin Wraith, heads or tails, makes a backup script copy when only half of what it
  needs is there. The Sage Owl teaches it on the adventure's Logic road too, with a chest to open and
  new questions.
- Three new lessons fill gaps at the start of the path. "Help yourself" shows how to read `--help`,
  `man` and an error message, so you're never stuck for long. "Editing a file in the terminal"
  teaches nano or vi: Bashou asks which one when you start (`bashou config editor` changes it), and
  the hints of the fights where you fix a file show that editor's keys. "Patterns" is a gentle first
  taste of regular expressions, just what `awk` and `sed` need next.
- Logic now comes before quotes and scripts, since scripts are full of `if` and `&&`, and git comes
  after scripts.
- The first time you open a lesson, the Sage Owl warms you up with two questions about the lessons
  just before it, with the explanation either way. Esc skips it.
- Five new first fights for the start of the path, each with its lesson: the Flag Phantom makes you
  find the option that ignores capitals in `sort --help`, the Typo Troll leaves a typo to fix in your
  editor, the Clutter Critter scatters photos and documents to tidy into folders with `mkdir` and `mv`,
  the Glob Goblin piles up reports to remove with one wildcard (and only the right ones), and the Core
  Counter asks how many processors your computer has (`nproc`). On the adventure, the Sage Owl teaches
  "Files and editing" and "Help and wildcards" on the road, each followed by a chest, and new questions
  join the quiz.
- A lesson also opens the ones after it when you use its command and it works: once for the lessons
  many others wait for (like `man` for "Help yourself", `nano` or `vi` for the editor, `mv` for files),
  three times for the others: `grep`, `find`, `tar`, `git`, `chmod`, `ps`, `gcc`, `dig` and many more.
  A command counts inside a pipe too (`cat app.log | grep error | sort` counts for grep and sort), as
  long as the whole line works. The Sage Owl lists these commands among the ways to pass a lesson.
- Five new shell fights, one for each lesson they practise: the Stderr Stalker hides error lines among
  normal ones until you catch them with `2>`, the Space Sprite slips a space into a file name (quotes
  save you), the Shebang Shade breaks a script's first line and its right to run, the Rename Rat
  needs a `for` loop to rename every photo, and the Pattern Pixie mixes fake parcel codes that only a
  precise `grep -E` pattern sees through. On the adventure, the Sage Owl teaches "Streams and scripts"
  on the road, with a chest, and new questions join the quiz.

## v0.6.5 — 2026-09-29

- C fights no longer refuse a correct fix at random. On some systems (gcc 12, as on Debian 12, with a
  recent kernel, WSL included), a program built with AddressSanitizer could freeze when it started,
  about one time in three, and the check gave up. Bashou now runs your program with address
  randomization turned off, which prevents that. Where that isn't allowed, it builds without the
  sanitizer, and the two memory fights that need it wait for a system that can run them.
- A save damaged inside (one wrong byte on disk, or a hand edit) no longer makes your pet crash over
  and over. The damaged entry is dropped and everything else in your save is kept. If the starter
  itself can't be read, Bashou asks you to choose it again.
  A setting damaged the same way (a bubble range that isn't one) is set back to its default too.
- Your pet's tips follow a path now. Each family's achievements lead one to the next (`grep -r`, then
  `grep -E`, then `grep -C`), and your pet suggests the next one on the path, the same one until you
  earn it, instead of a random easy one each time.
- The pet board, the library and the first-launch screens fit a narrow (portrait) terminal: the
  board shows fewer pets per row, and the keys (q: quit…) go on their own line instead of being cut off.
- In the adventure, your pet stays in view when a monster, a boss or a chest asks you something: the
  question box sits between you and what you meet, instead of hiding your pet. On an 80×24 terminal
  your pet is drawn smaller so everything fits.
- In the adventure, the paths at a fork keep the same thickness all along, instead of jumping
  between one and two pixels from line to line.
- The adventure looks right in a tall, narrow (portrait) terminal. The status line at the bottom was
  cut off, hiding your chapter, hearts and meters: when it doesn't fit, it now takes two lines. And
  between forks your pet walked under an empty sky: a road now runs ahead of it to the horizon, and
  what waits for you comes down that road.
- For contributors: the code was reworked toward a data-driven program. The save, the commands, the
  achievement chains, the skills and the settings are each described in one place, instead of several
  copies that had to agree. That removes a whole kind of bug, where one copy was updated and another
  was not.

## v0.6.4 — 2026-09-28

- The Pebble's last evolution, at level 20, really changes your pet now: the Jade golem was only a
  green Crystal golem, so it said it was evolving and looked the same. It's now a carved jade pendant
  with a grinning face, hanging from its cord.
- Stars now count forms: one star per form, filled up to the one your pet has reached (★★☆ for a Bat,
  ★★★★★★★☆☆☆ for a Packet at its 7th form). The pet screen and the board used to disagree, and pets with
  many forms stopped saying what comes next after their third.
- The Hacker cat stays once a secret brings it. It used to leave at every load, then say "New pet:
  Hacker cat!" again after each command. Its picture also shows on the pet screen now.
- Two pairs of achievements shared a name inside the game, so earning one counted as both: the Snail's
  and the Spark's **Scholar**, and the Axolotl's and a secret **Mapper**. Using `jq 'map(...)'` could
  bring the secret Hacker cat without finding any secret. Each now counts on its own. A Hacker cat you
  already have stays.
- For contributors: a new pet, or a new form, is now only JSON files. Each pet has a family file (name,
  place on the board, how it's unlocked, what it says), and each form names the form it evolves into and
  what it takes. The tests check every pet from these files (see `doc/contributing/pixel-art.md`).

## v0.6.3 — 2026-09-28

- If you installed the apt or dnf package but your `~/.bashrc` still loaded an old git copy of Bashou,
  your terminal kept running that old copy, which the package manager never updates (so `bashou share`
  was missing, for example). Now the package moves those terminals to itself when they open. It works
  in every terminal on Fedora and Rocky, and in login shells on Debian and Ubuntu. `bashou update` in
  a git copy also updates it again, instead of offering the package you already have. If a terminal
  still shows an old version, run `bashou update --version v0.6.3` once, then open a new terminal.
- The pet and its speech bubble no longer hide or eat lines of text. Before, they were drawn over the
  top of the screen, and when you scrolled up, a long output like `--help` had holes where they had
  been. Now Bashou moves those top lines up (where scrolling finds them, untouched) before drawing the
  pet, and removes the empty space again when your next command starts. Terminals that can't say
  where the cursor is keep the old behavior. The fight panel in the arena makes room the same way, and
  pressing Enter on an empty line no longer stacks copies of the pet one under the other.
- In a terminal opened before this update, the pet can't make room yet: it tells you once to open a
  new terminal (or type `exec bash`) instead of drawing over your text.
- The Bat's night achievement is now called **Night shift** (it was "Night owl", and players looked for
  an Owl to unlock). Every achievement note now says which pet family it grows: "🏆 Night shift (Bat
  family): …".
- A shorter `bashou --help`, with one command per job:
  - `bashou explain` is gone: the lessons explain the same things better, with drawings. In a code,
    Rust or network fight, type `lesson` to open the one that explains it.
  - `bashou on` also does what `bashou setup` did: after installing the apt or dnf package, `bashou on`
    adds Bashou to your `~/.bashrc`.
  - The language and the skills live in `bashou config`: `bashou config language` (or
    `bashou config language fr`), `bashou config skills`. `bashou config list` shows them too.
  - The old names (`bashou setup`, `bashou language`, `bashou skills`) still work.
- The IPv4 addresses lesson mentions `ipcalc`, which does the network math in one command.
- **`bashou arena`**: come and fight when you want, without waiting for a threat. Pick a timed
  fight (hearts and a clock shown in the prompt: 5, 8 or 12 minutes by level) or a security
  investigation (no clock). Lose, run out of time or flee, and the arena closes for an hour;
  threats your pet announces can still be fought with `bashou fight`. The security investigations
  moved here: `bashou arena security 3` (the old `bashou security` leads there too).
- `bashou help` (and `bashou --help`) lists the commands by what they're for: your pet, learn, play,
  settings. In French too.
- `bashou learn` is easier on the eye: the command in color (commands, options, arguments and
  operators each in their own color), then each command as a numbered step with one line per option
  (`-czf` becomes `-c`, `-z`, `-f`), in normal text instead of grey.
- `bashou learn` now knows grep's `-v`, `-i`, `-l`, `-c`, `-o`, `-w` and `-F`, and after
  `find … -exec grep -l …` the `-l` is grep's, not find's.

## v0.6.2 — 2026-09-26

- `bashou share` asks for a nickname the first time and puts it on every card, so the banner never
  needs your real name (`bashou share --name` changes it).
- The banner also shows your starter at its latest form, and speaks English or French: it follows your
  browser's language, and two buttons switch it before you share.
- The Ember is redrawn cleaner: a symmetric flame on a smooth bed of charcoal.
- The README shows a sample banner and says it plainly: Bashou collects nothing, you are not the
  product.
- Each release now carries its `.deb` and `.rpm` with signed checksums and a build provenance
  attestation, so you can check a download came from this repository (see the guide).

## v0.6.1 — 2026-09-25

- The Ember lost the stray pixel floating at its top right.

## v0.6.0 — 2026-09-25

- **New skill: Network.** Tick it in `bashou skills` to learn IPv4, IPv6, DNS and TCP with real tools.
  - Six lessons in the Sage Owl's library, from what `192.168.1.20/24` means to a troubleshooting
    ladder that goes from the cable up to the application, one command per step.
  - Ten fights against network creatures: find the port a listener hides on with `ss`, your own address
    and route with `ip`, which hosts sit in a /22, what `getent` returns against DNS, and, in saved
    captures read with `tcpdump -r`, the handshake that never finished, the refused connection and the
    name that got NXDOMAIN. Their little servers listen on 127.0.0.1 or ::1 only: nothing leaves your
    machine. On the adventure road, a new chest opens with `ss` on IPv6.
  - 37 adventure questions in a new topic, guarded by the Latency Kraken.
- **New pet: the Packet**, from a single Bit to a Constellation of satellites, in ten forms. It comes
  after ten uses of `ip`, `ss`, `ping`, `getent` and friends, and grows with twelve network achievements.
- The Rocky Linux path starts gentler: level 1 asks about installing, removing, searching and updating
  with `dnf`, and SELinux, EPEL and automatic updates come at level 2, once the basics are known.
- **New: `bashou share`.** It shows a QR code; scan it and your phone draws a banner of your pet, level
  and progress, with a Share button for Signal, WhatsApp or any app. Before the QR code, it lists
  exactly what the card contains. The data travels in the link after the `#`, which browsers never
  send to a server, and `--name` adds a short nickname if you want one.
- `bashou learn` now explains `ip`, `ss`, `ping`, `getent`, `host`, `resolvectl`, `tracepath`,
  `traceroute`, `nc` and `tcpdump`, and `bashou explain network` has notes on CIDR, IPv6, DNS and TCP.
- On Rocky, Fedora and Red Hat, `bashou update` now runs `sudo dnf upgrade --refresh bashou`: plain
  `dnf upgrade` could say "Nothing to do" for two days after a release, because dnf keeps its list of
  packages that long. The Bashou repository file now asks dnf to check it every 6 hours.

## v0.5.0 — 2026-09-25

- **New: `bashou lesson`, the Sage Owl's library.** Hints tell you what to type; lessons show how things
  work. Each lesson is a few short pages with a drawing that grows from one page to the next, and the owl
  points its wing at what matters: how the shell reads a command line, what the CPU and the RAM do, the
  file tree, stdout and stderr, pipes step by step, permissions, processes and signals, packages and
  their signatures, systemd services, how gcc compiles a program, the stack and the heap in C, pointers and strings, Python names, Rust variables, SQL joins,
  public and private keys, CI pipelines. Lessons unlock with your fights and achievements, each one
  preparing your next step, and the locked ones tell you what opens them. The lessons that make you
  progress now are green; once your fights and achievements show you've mastered one, it turns white.
  Your pet mentions it when a new one is waiting.
- **A new pet: the Spark, born from the library.** Fire, for the Library of Alexandria that burned and for
  the books still destroyed today: what you learn, nobody can burn. Read a lesson to the end and a few
  Sparklings twinkle next to you. They grow with each lesson achievement (read 3, 6, 12 and 20 lessons,
  master 1, 5 and 10, three skills) through Spark, Ember, Candle, Lantern, Torch, Campfire, Beacon and
  Blaze, and become a Phoenix when you've read every lesson of your skills. Learning only one skill? The
  counts stop at what your skills offer, so the Phoenix stays within reach.
- **Fifteen short lessons for the basics**, each building on the one before: files (mkdir, cp, mv, rm),
  reading files (cat, less, head, tail -f), wildcards, shell variables, quotes, grep, users and sudo, disk
  space, archives with tar, your first script, loops, addresses and ports, git snapshots and branches,
  your first Python script and your first SQL SELECT. Every lesson is in French too.
- **gcc and gdb get their own fights and lessons.** Four new C fights: the Linker lynx (a program in two
  files), the Warning wraith (a bug only `-Wall` shows), the Segfault salamander (find the crashing line
  with gdb's backtrace) and the Breakpoint beetle (stop a loop at the right month with a conditional
  breakpoint). Two library lessons, "Using gcc" and "Debugging with gdb", a Sage Owl road lesson and a gdb
  chest, 8 new C questions, and `bashou explain c link`, `warnings` and `gdb`.
- **Modern tools where it helps**: the compilation lesson now shows clang, sanitizers, clang-tidy and
  cargo/go, the gcc lesson CMake, Meson and Ninja, the gdb lesson lldb, rr and editor debuggers.
- **Every fight now has a lesson.** Eight new lessons fill the gaps: wc, sort, cut and uniq; awk and sed;
  find; Python loops, dicts and recursion; reading JSON, base64 and %XX safely in Python; package
  repositories on Debian and Rocky; SQL CREATE, INSERT, UPDATE and upsert; and pass. As soon as you meet a
  fight, its lesson opens, and typing `lesson` in the arena reads it without leaving the fight.

## v0.4.3 — 2026-09-24

- The Seedling is now a little seed with one shoot, so you can tell it apart from the Sprout.
- A speech bubble closes as soon as you run the command it suggests (`bashou fight`,
  `bashou evolve`…), and never stays more than 3 minutes.
- **A new pet: the Snow leopard.** A shy cat that keeps secrets: use gpg or pass 5 times and the Snow cub
  joins you, then grows into a Snow leopard and a Mountain ghost as you encrypt files, make a key, start a
  password store and hand passwords to commands with `$(pass show …)`. No gpg or pass yet? Your pet tells
  you how to install them.
- **Two new Slime forms.** At 3,500 commands your Slime freezes into an Ice slime, a little crystal
  cluster, and at 7,500 it becomes a Thunder slime, a grumpy storm cloud. A Cat or King slime you
  already have stays what it is.
- **A new pet: the Duck.** Debug like a programmer with a rubber duck: explain a command with
  `bashou learn`, trace a script with `bash -x`, check it with `bash -n` or read `echo $?`, and a
  Duckling waddles in. Each new habit brings a new form: a Duck, a White duck, and at last a Mandarin
  duck (with `shellcheck` too, if you have it).
- **Learn SQL with SQLite.** A new skill and adventure path: the Sage Owl explains databases, SELECT,
  JOIN, CREATE TABLE, INSERT, UPDATE (always with a WHERE) and INSERT … ON CONFLICT DO UPDATE, with a
  chest to open and 22 questions. Six new threats hand you a database to query or fix, from the Query
  Quokka to the Upsert Unicorn. SQLite keeps a whole database in one file, so nothing is left behind:
  delete the file and it's gone. No sqlite3 yet? Your pet tells you how to install it.
- **Keep secrets with gpg and pass.** The Sage Owl explains locking files, key pairs, signatures and
  the pass password store, with a chest to open and 6 new Linux questions. Five new threats: lock a file
  (Plaintext Pixie), open one (Cipher Crow), tell a genuine download from a forged one with gpgv (Forger
  Ferret), read a password store (Vault Vole) and take a password out of a script with
  `$(pass show …)` (Cleartext Cricket). The fights bring their own practice key and store: your keys
  and passwords are never touched. In fights, gpg now asks for passphrases right in the terminal.
- **`bashou update` helps you move to apt or dnf.** On a git install on Debian, Ubuntu or the Red Hat
  family, it offers once to switch to Bashou's signed repository: it shows every command first (key,
  repository file, install), asks, runs them in front of you and updates your `~/.bashrc` (with a backup).
  Later: `bashou update --packages`. On a package install, it shows the apt or dnf command and offers
  to run it. The README now shows the apt and dnf install first.
- **What you type stays private.** Bashou's folders were readable by other accounts on systems where
  home folders are (Debian's default): they are now yours only, and existing ones are tightened. Events
  left by terminals that closed badly are removed. `.github/SECURITY.md` lists everything Bashou writes.
- On Rocky, Alma and RHEL, the Process Phantom could not be found (its name got lost), so that fight
  couldn't be won. It shows up in `ps` again.
- The Leak Lurker and the Fencepost Fiend only come where gcc can use AddressSanitizer: without it, their
  bug was invisible and the fight was won before it started.
- CI now also runs every test on Rocky Linux 9, and installs the .rpm there.
- Pets and fights no longer slow down when many tools are missing (on WSL, looking for a missing
  command searched every Windows folder).

## v0.4.2 — 2026-09-23

- **Install with apt or dnf.** Bashou now has its own signed repositories for Debian, Ubuntu, Rocky,
  Alma, RHEL and Fedora: add the repository once, then `apt install bashou` or `dnf install bashou`,
  and updates come with the rest of the system. Each user who wants a pet runs `bashou setup`.
- **Choose what you learn.** At the first launch, pick a bit of everything or tick your skills
  (Bash, Linux, systemd, Debian, Rocky, Python, C, Rust, Logic, CI/CD): threats and adventure paths
  follow. `bashou skills` changes it any time.
- `bashou config` asks you a few questions and saves the answers (bubble length, pet size, how often
  your pet talks, updates, skills, language). `bashou config list` still lists everything.
- **Learn to read `--help`.** For your first 5 wins, a fight's first hint shows how to ask the tool
  itself (`wc --help`), how to read the Usage line and the options, and what to look for this time.
  `--help` and `man` are free moves in a duel.
- Bashou no longer runs a `bashou` folder found in the directory you're in instead of its own code.
- **Your progress is safer.** If your save gets damaged, Bashou keeps it aside
  (`state.json.broken-…`) and brings back the last good copy (it keeps one a day) instead of
  crashing or starting over. Saves from every earlier version still load.
- Very old installs (from before 0.1.0) whose `bashou update` stops with "Not possible to
  fast-forward" can't update themselves. Move them to this release once:
  `git -C ~/.bashou fetch --tags && git -C ~/.bashou checkout v0.4.2`. Your progress is kept.
- The starter screen no longer shows a line of question marks under each starter.
- **`verify` or `answer`, never both.** Fights and chests where you do the job (fix a file, make a
  folder…) end with `verify`: Bashou checks your work. Those that ask a question end with
  `answer <value>`. Each screen shows only the one that applies, and typing a command after `answer`
  tells you to run it at the prompt instead.
- After an update, your save is upgraded to the new format on disk, and a copy of the old one is
  kept next to it.
- **Adventure answers that teach.** After each question, the right answer now stands on its own line,
  followed by a real explanation in plain words: why it's right, what the tempting wrong answer
  does, and what to do next. All the questions, in English and French; many questions also give
  more context.
- **Why sort comes before uniq.** uniq only merges identical lines that follow each other, so
  `cut … | uniq -c` counted the same city several times. The Sage Owl's pipe lesson now says so, the
  cities chest explains it in its hints, and the arena tells you once when you run uniq without sort.
- **sort, taught at last.** The Sage Owl has a new lesson on sort (alphabetical, -n for numbers,
  -rn | head for a top list, and why sort comes before uniq), two chests to practice it, and new
  questions on sort and uniq.
- The Slug has a new look: olive green, big eyes on stalks, pink cheeks and a smile.
- During a boss fight, the pet no longer flashes under the question box.
- Moving on the swap board no longer leaves pieces of text behind.
- **CI/CD fights.** Five new threats hand you a pipeline file to fix: a GitHub Actions workflow with a
  line indented wrong (Indent Imp), a token written in clear (Secret Sprite), a deploy that neither
  waits for the tests nor stays on main (Needs Newt); a .gitlab-ci.yml with a stage that doesn't
  exist (Stage Specter) or a production deploy that should wait for a click (Manual Mole). The
  Sage Owl teaches pipeline files on the CI/CD path, with a chest to practice, and six new CI/CD
  questions go with them.
- **The road splits.** At a fork, the road now divides in front of your pet into two or three paths
  fading into the distance, each with its name written at its end; the one you pick lights up.

## v0.4.1 — 2026-09-23

- **Beaten fights come back, so you keep what you learned.** A fight you win returns the next day,
  then 7 days later, then 30 days later; win that one and the tool is acquired. Your pet says when a
  threat is a review, and a lost review starts over the next day. Fights you had already won are
  spread over the coming days. The guide explains why (spaced repetition).
- **Rust fights**, where `rustc` is installed: a counter that isn't `mut`, a `const` without its
  type, text that should become a number (shadowing, since `mut` can't change a type), and a `u8`
  total that overflows. Each file says what it must print and how to build it (`rustc counter.rs`).
- `bashou explain rust mut` (or shadowing, const, integers).
- **A Logic path in `bashou adventure`**, for beginners in any language: what a variable holds
  after a few lines, `and` / `or` / `not`, how many times a loop runs, where a counter starts, indexes
  from 0, `return` versus `print`, then loops that never end, off-by-one, short-circuits and De Morgan.
  30 questions and a Paradox Sphinx.
- **Automatic security updates** in the Debian and Rocky questions: turning on unattended-upgrades
  and dnf-automatic, keeping them to security fixes, a dry run, their timers, keeping one package
  out, and what's still left to do after they ran (restarting services, rebooting, going back with
  `dnf history undo`). Rocky gets its first level 3 questions.
- Four new first-level Rust questions in `bashou adventure`: `mut`, shadowing, `const`, overflow.
- Once you have 15 achievements and no Rust yet, your pet sometimes offers to start: it gives the
  install command for your system (`apt`, `dnf`, or rustup, read before you run it).

## v0.4.0 — 2026-09-23

- **Code fights.** Fifteen new threats, in Python and C. Most hand you a small broken file whose
  first lines say what goes in, what should come out and how to run it; fix it, and Bashou runs its
  own tests on your version. The first ones only ask to make the code compile (a missing `:` in
  Python, a missing `;` in C). Then lists, dicts, loops and recursion in Python, and memory, arrays,
  recursion and a buffer overflow in C, checked with AddressSanitizer. Others take a `python3 -c`
  one-liner: read a JSON config, decode base64, decode a URL-encoded attack, read what a JWT says.
  One more asks you to stop a shell injection.
- **Package fights, on your own machine.** On Debian and Ubuntu: which version of a package is
  installed (`apt list --installed`), which version apt would install (`apt search`, `apt policy`),
  which package put a file in /usr/bin (`dpkg -S`), and whether a package is marked manual or auto
  (what `apt autoremove` looks at). On Rocky, Alma, Fedora and Red Hat: the installed version
  (`rpm -q`), which package owns a file (`rpm -qf`), how many packages are installed. Bashou reads
  /etc/os-release and only sends the ones for your system.
- **Repository fights.** Fix a `debian.sources` (or a Rocky `.repo`) with three planted mistakes:
  look the right values up online or in your own /etc. On Red Hat, the Enabled Ettin asks for one
  dnf command limited to a single repository: `--disablerepo='*' --enablerepo=<id>`.
- `python3 -m bashou.creatures show <pet or fight id>` draws a fight's enemy with all its poses.
- `bashou explain python list` (or dict, loop, recursion, json, url, base64, subprocess;
  `bashou explain c malloc`, array, string, recursion, asan) gives a short note with an example,
  offline.
- Opening a text editor in the arena no longer costs a heart.
- The quiz questions of `bashou adventure` were rewritten to teach habits that last in automation
  and security (what goes wrong, what to check first, what an output means) instead of trivia.
  New: a systemd topic about writing units, and level 3 questions for Debian and Linux.
- Your pet waits for a pause in your work before it talks, about every 10 to 20 minutes.
  `bashou config talk` and `bashou config quiet` change that.
- The start and the forks of `bashou adventure` no longer cover the road with a box: the chapter or
  the ways you can go sit on the top line, the keys (Enter, ←/→) on the bottom line.
- Fixed: a question with a `%` in it crashed the adventure.

## v0.3.1 — 2026-09-22

- **Ten new fights, and the easy ones come first.** Your first threats now ask for one command with
  at most one option: count the lines of a file (`wc`), print a column (`cut`), sort names, read the
  end or the start of a file (`tail`, `head`), find someone in a list (`grep`), list a folder (`ls`),
  print one line (`sed -n`). The tool fights (grep, awk, find, uniq, sed, ps) only come once you have
  met their tool, and the Knot Eel's pipeline stays last.
- The first hint of every new fight points at the help: `bashou learn <command>` and `--help`.
- Each new threat has its own look: Line Moth, Column Crab, Jumble Sprite, Last-word Wisp,
  First-line Imp, Needle Gnat, Field Wasp, Dust Bunny, Verse Viper and Peak Harpy.
- `bashou learn` explains `uniq -u` and `uniq -d`, and says that uniq only compares neighbouring
  lines, so you sort first.
- The Sand grain rides a pale blue gust that curls into a spiral, and no longer shows twice when the
  wind catches it mid-breath.
- The Leaf slime is a leaf: veins from the foot of its midrib to the sides, a pointed tip, and it
  breathes out an O2 bubble instead of flapping.

## v0.3.0 — 2026-09-22

- Every starter now has **7 forms** and grows to level 20 (one level per 5 achievements). New shapes
  at levels 3, 5, 8, 11, 15 and 20; what your pet becomes is a surprise, and a form once reached is
  never lost.
- Pets come from what they stand for. Your command count grows a Droplet that changes shape 6 times
  on the way to 10,000 commands, while the other pets come from your first programs, your own
  scripts, walks and right answers in the adventure, and fights won or lost. Pets you already have
  stay yours.
- Secret achievements. Nothing tells you what they are; they show up when they show up, and the
  first one brings a pet that isn't on the board.
- The Slime's old achievements (`$( )`, heredocs…) join the Mushroom, which is about scripting.
- No spoilers: the swap board, the starter choice and `bashou level` show only what you've reached,
  and the level of the next form.
- Sprite fixes: the Droplet, the Orc's tusk and the Snakelet are symmetric again.

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
