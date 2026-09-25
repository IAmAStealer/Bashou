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
  (`tests/test_lesson.py` checks it). Meeting a fight opens its lessons even if their `needs` don't
  hold yet, and `lesson` in the arena opens the lesson right there.
- **Aim for one lesson for about three fights.** A lesson covers an idea (text columns, C memory, SQL
  writes), not one fight.
- **The next step, not the current one.** `needs` open a lesson just before the player needs it:
  a few commands more, the first fight of a skill, the tool used once. Never "read lesson X".
- **Short steps that stack.** Each lesson uses only what earlier lessons in its track taught, and
  says so when it builds on one ("see the lesson on keys").
- **Mastered means done, not read.** `masters` names the fights and achievements that prove it.

## Tracks

Lessons in library order (`order`), with the fights they prepare.

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

### CI/CD

1. `pipeline` — stages, needs, rules, secrets · Indent Imp, Stage Specter, Needs Newt, Secret Sprite,
   Manual Mole

## Known gaps

- **Logic** (coding basics) has adventure questions but no lesson and no fights.
- **systemd** and **Rust** stop after one lesson: next steps would be timers and journalctl filters,
  ownership and borrowing, each with fights.
- **Bash** has no fights yet for scripts, loops and quotes; **Linux** none for users, permissions,
  disk, archives and network (their achievements master those lessons).
