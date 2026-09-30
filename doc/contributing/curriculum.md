# Teaching plan

How Bashou's pieces work together to take a player from their first command to real work, one small step
at a time. Read this before adding a lesson, a fight or questions: each new piece should fill a step
of a track below.

## Four layers, one topic

| Layer | What it does | Where |
|---|---|---|
| Adventure questions | recognize the right idea among wrong ones | `bashou adventure` |
| Lessons | show **how it works**, with a drawing, before you need it | `bashou lesson` |
| Fights | do it for real in a sandbox, with hints down to a working command | `bashou fight` |
| Reviews | a beaten fight comes back later, so it sticks | `fight.py` (`INTERVALS`) |

A topic is complete when it has all four: questions, a lesson, one or more fights with hints, and
(for fights with a new tool) a Sage Owl road lesson and chest in the adventure.

## Rules

- **Nobody is stuck on a fight.** Every fight is in the `fights` list of at least one lesson
  (`tests/test_lesson.py` checks it). Meeting a fight opens its lessons even if the lessons before
  them aren't passed yet, and `lesson` in the arena opens the lesson right there.
- **Aim for one lesson for about three fights.** A lesson covers an idea (text columns, C memory, SQL
  writes), not one fight.
- **A real path (owner, 2026-09-30).** `after` lists the lessons that come first; a lesson opens once
  each of them is **passed**: one of its fights won, one of the achievements in its `masters`, or
  3 achievements in all per step of depth (depth = the longest path from `command_line`, which is 1).
  Reading a lesson never opens the next one: doing does. No counters (`commands N`) any more. A lesson
  of a skill the player doesn't learn doesn't block, and a lesson already opened stays open.
- **Cross links.** Paths cross themes where one idea needs another: Python and C wait for shell
  scripts, loops and Logic; SQL waits for text columns; CI/CD for git, scripts and pass.
- **Short steps that stack.** Each lesson uses only what earlier lessons in its track taught, and
  says so when it builds on one ("see the lesson on keys").
- **Mastered means done, not read.** `masters` names the fights and achievements that prove it.

## Paths between lessons

`A → B`: B comes after A. `A + B → C`: C needs both.

- First steps: command_line → computer; command_line → paths → files → reading → wildcards →
  variables; files + reading → git
- Bash: reading → streams; reading → grep; streams + grep → pipes → text_tools → awk_sed;
  wildcards → find; variables + streams → quotes → scripts → loops
- Linux: files → users → permissions → keys; keys + scripts → pass; files → disk;
  disk + find → archives; computer + users → processes
- systemd: processes + streams → services
- Packages: users → packages; packages + network → repos
- Network: processes → network → ip_addr → ipv6; ip_addr → dns → dns_tools; ip_addr → tcp;
  dns_tools + tcp → net_debug
- Logic: variables → logic
- Python: scripts + loops + logic → py_start → py_flow → py_names; py_names + pipes → py_data
- C: computer + scripts + logic → compilation → gcc_use → stack_heap → pointers → debugger
- Rust: stack_heap → rust_vars
- SQL: text_tools → sql_select → sql_write → sql_join
- CI/CD: git + scripts + pass → pipeline

## Tracks

Lessons by theme, with the fights they prepare. The library lists them in `order`, which follows the
paths above.

### First steps (everyone)

1. `command_line` — how the shell reads a line
2. `computer` — CPU, RAM, disk
3. `paths` — the file tree · Dust Bunny
4. `files` — mkdir, cp, mv, rm
5. `reading` — cat, less, head, tail · First-line Imp, Last-word Wisp
6. `wildcards` — * and ?
7. `variables` — shell variables, $( ), export
8. `git` — commits and branches

### Bash (text tools)

1. `streams` — stdout, stderr, redirections
2. `quotes` — ' and "
3. `grep` · Needle Gnat, Log Hydra
4. `text_tools` — wc, sort, cut, uniq · Line Moth, Column Crab, Jumble Sprite, Peak Harpy, Echo Swarm
5. `pipes` — chains, step by step · Knot Eel, Echo Swarm, Peak Harpy
6. `awk_sed` — columns and edits · Field Wasp, Ledger Golem, Verse Viper, Typo Serpent
7. `find` · Maze Wraith
8. `scripts` — shebang, arguments, set -euo pipefail
9. `loops` — for, while read

### Linux

1. `users` — uid, groups, sudo
2. `permissions`
3. `disk` — df, du
4. `archives` — tar
5. `processes` — ps, signals · Process Phantom
6. `network` — addresses, ports, listening
7. `keys` — public and private keys · Plaintext Pixie, Cipher Crow, Forger Ferret
8. `pass` — a password store · Vault Vole, Cleartext Cricket

### Packages (Debian and Rocky)

1. `packages` — repositories, signatures, dependencies · Version Vole, Release Raven, Stowaway Stoat,
   Census Centipede, Autoremove Adder, Hitchhiker Hare
2. `repos` — sources files, .repo files, asking apt and dnf ·
   Candidate Crow, Mirror Mimic, Repo Revenant, Enabled Ettin

### systemd

1. `services` — a service's life (no fights yet: its achievements master it)

### Logic

1. `logic` — yes/no answers, if, !, && and || · Negation Gnome, Or Ogre

### C

1. `compilation` — source to program, reading errors · Semicolon Slug
2. `gcc_use` — warnings, several files, libraries, build tools · Linker Lynx, Warning Wraith
3. `stack_heap` · Leak Lurker, Stack Specter
4. `debugger` — gdb · Segfault Salamander, Breakpoint Beetle
5. `pointers` — arrays and strings · Fencepost Fiend, Overflow Ogre

### Python

1. `py_start` — first script, blocks, SyntaxError · Colon Cobra
2. `py_flow` — loops, dicts, recursion · Dict Djinn, Loop Lich, Ouroboros
3. `py_names` — names and objects · List Leech
4. `py_data` — JSON, encodings, injection · JSON Jinn, Base64 Banshee, Percent Poltergeist,
   Token Trickster, Injection Imp

### Rust

1. `rust_vars` — let, mut, shadowing, integer types, const · Mut Marmot, Const Condor, Shadow Shade,
   Byte Basilisk

### SQL

1. `sql_select` · Query Quokka
2. `sql_write` — CREATE, INSERT, UPDATE, upsert · Table Troll, Insert Imp, Update Urchin, Upsert Unicorn
3. `sql_join` · Join Jackal

### Network

1. `network` — addresses and ports (also in Linux)
2. `ip_addr` — IPv4 addresses, prefixes, the gateway · Address Adder, Subnet Sprite, Route Raven
3. `ipv6` — reading and shortening, link-local, /64 and SLAAC · Six Serpent
4. `dns` — the resolution chain, records, TTL · NXDomain Nixie
5. `dns_tools` — dig, getent, resolvectl · Resolver Rook, NXDomain Nixie
6. `tcp` — the handshake, ports, states · Loopback Lurker, Handshake Heron, Established Ettin
7. `net_debug` — the troubleshooting ladder · Refused Revenant, Established Ettin, Handshake Heron

### CI/CD

1. `pipeline` — stages, needs, rules, secrets · Indent Imp, Stage Specter, Needs Newt, Secret Sprite,
   Manual Mole

## Known gaps

- **systemd** and **Rust** stop after one lesson: next steps would be timers and journalctl filters,
  ownership and borrowing, each with fights.
- **Bash** has no fights yet for scripts, loops and quotes; **Linux** none for users, permissions,
  disk, archives and network (their achievements master those lessons).
