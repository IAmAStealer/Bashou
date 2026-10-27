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

- First steps: command_line → computer; command_line → help → paths → files → editor → reading →
  wildcards → variables; variables + wildcards → bash_zsh
- Bash: reading → streams; reading → grep → regex; streams + grep → pipes → text_tools;
  regex + text_tools → awk_sed; wildcards → find; variables → logic; logic + streams → quotes →
  scripts → loops; scripts → substitution; scripts → git → git_fix
- Bash scripts (skill `script`, owner 2026-10-22: bash at the prompt and bash in scripts are two jobs):
  quotes → scripts → prompt_script → script_errors → script_files → script_data;
  script_errors → script_cleanup
- Linux: files → users → permissions → keys; keys + scripts → pass; files → disk;
  disk + find → archives; computer + users → processes
- systemd: processes + streams → services
- Packages: users → packages; packages + network → repos
- Network: processes → network → ip_addr → ipv6; ip_addr → dns → dns_tools; ip_addr → tcp;
  dns_tools + tcp → net_debug; keys + net_debug → certs → certs_tools → certs_admin → certs_ca → certs_cnf → certs_revoke
- Logic: variables → logic
- Python: scripts + loops + logic → py_start → py_flow → py_names; py_names + pipes → py_data
- C: computer + scripts + logic → compilation → gcc_use → stack_heap → pointers → debugger
- Rust: stack_heap → rust_vars → rust_own
- SQL: text_tools → sql_select → sql_write → sql_join
- CI/CD: git + scripts + pass → pipeline

## Warm-up

The first time a lesson opens, the library asks 2 questions from the `recall` lists of the lessons
before it (adventure question ids), explanation shown either way, Esc skips. Recall comes back
right when it's needed, on the brick you're about to build on. Every lesson has a `recall` list.

## Tracks

Lessons by theme, with the fights they prepare. The library lists them in `order`, which follows the
paths above.

### First steps (everyone)

1. `command_line` — how the shell reads a line
1. `help` — --help, man, reading an error message · Flag Phantom
2. `computer` — CPU, RAM, disk · Core Counter
3. `paths` — the file tree · Dust Bunny
4. `files` — mkdir, cp, mv, rm · Clutter Critter
4. `editor` — nano or vi (`bashou config editor`): open, change, save, quit · Typo Troll
5. `reading` — cat, less, head, tail · First-line Imp, Last-word Wisp
6. `wildcards` — * and ? · Glob Goblin
7. `variables` — shell variables, $( ), export
7. `bash_zsh` — where zsh reads a line differently: word splitting, patterns that match nothing, arrays
   from 1, and the first line of a script that picks its shell (0.9.0) · Index Imp
8. `git` — commits and branches · Commit Crowd, Branch Bramble
9. `git_fix` — merge conflicts, stash, restore, revert vs reset · Conflict Chimera, Revert Revenant

### Bash (text tools)

1. `streams` — stdout, stderr, redirections · Stderr Stalker
2. `quotes` — ' and " · Space Sprite
3. `grep` · Needle Gnat, Log Hydra
3. `regex` — a first taste of patterns, enough for awk and sed · Pattern Pixie
4. `text_tools` — wc, sort, cut, uniq · Line Moth, Column Crab, Jumble Sprite, Peak Harpy, Echo Swarm
5. `pipes` — chains, step by step · Knot Eel, Echo Swarm, Peak Harpy
6. `awk_sed` — columns and edits · Field Wasp, Ledger Golem, Verse Viper, Typo Serpent
7. `find` · Maze Wraith
8. `substitution` — $( ) and backticks, quotes, exit code, pass in scripts
9. `loops` — for, while read · Rename Rat

### Bash scripts

Every script fight hands you a script built on the template (`bashou/challenges/template.sh`) with one
habit that is fine at the prompt and a bug in a script; `verify` runs your script again on its own tricky
input. Rules: [bash-style.md](bash-style.md).

1. `scripts` — shebang (env bash), arguments, the template, bash -n/-x, ShellCheck · Shebang Shade
2. `prompt_script` — the same job at the prompt and in a script: ls, echo, cd, --
3. `script_errors` — statuses, || die, set -e and its holes, local x=$( ), pipefail · Masked Mole, Errexit Eel
4. `script_files` — globs not ls, --, nullglob, find -print0, read loops and stdin · Dash Demon,
   Nomatch Nymph, Newline Nixie, Stdin Siren
5. `script_data` — printf, [[ ]], (( )), checking numbers, arrays · Echo Echidna
6. `script_cleanup` — mktemp, trap EXIT, ${dir:?} · Trap Troll

### Linux

1. `users` — uid, groups, sudo · Group Gremlin
2. `permissions` · Padlock Pest
3. `disk` — df, du · Bloat Blob
4. `archives` — tar · Tar Tortoise
5. `processes` — ps, signals · Process Phantom
6. `network` — addresses, ports, listening · Header Hound
7. `keys` — public and private keys · Plaintext Pixie, Cipher Crow, Forger Ferret
8. `pass` — a password store · Vault Vole, Cleartext Cricket

### Packages (Debian and Rocky)

1. `packages` — repositories, signatures, dependencies · Version Vole, Release Raven, Stowaway Stoat,
   Census Centipede, Autoremove Adder, Hitchhiker Hare
2. `repos` — sources files, .repo files, asking apt and dnf ·
   Candidate Crow, Mirror Mimic, Repo Revenant, Enabled Ettin

### systemd (in the Linux skill, Linux only)

1. `services` — a service's life · Unit Imp

### Logic

1. `logic` — yes/no answers, if, !, && and || · Negation Gnome, Coin Wraith

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
2. `rust_own` — ownership, moves, borrowing with & and &mut (opens once rust_vars is mastered)
   · Borrow Badger, Vector Viper

### SQL

1. `sql_select` · Query Quokka
2. `sql_write` — CREATE, INSERT, UPDATE, upsert · Table Troll, Insert Imp, Update Urchin, Upsert Unicorn
3. `sql_join` · Join Jackal

### Network

1. `network` — addresses and ports (also in Linux) · Header Hound
2. `ip_addr` — IPv4 addresses, prefixes, the gateway · Address Adder, Subnet Sprite, Route Raven
3. `ipv6` — reading and shortening, link-local, /64 and SLAAC · Six Serpent
4. `dns` — the resolution chain, records, TTL · NXDomain Nixie
5. `dns_tools` — dig, getent, resolvectl · Resolver Rook, NXDomain Nixie
6. `tcp` — the handshake, ports, states · Loopback Lurker, Handshake Heron, Established Ettin
7. `net_debug` — the troubleshooting ladder · Refused Revenant, Established Ettin, Handshake Heron
8. `certs` — what a certificate says, the chain, the SAN, expiry · Expiry Elk, SAN Salamander
9. `certs_tools` — openssl x509, s_client, verify, curl's errors · Key Kobold, Chain Chameleon
10. `certs_admin` — CSR, private CA and trust store, renewal, key safety · Request Raccoon, Insecure Iguana
11. `certs_ca` — basicConstraints, pathlen (depth), keyUsage, reading verify errors · Pathlen Panther, Impostor Ibex
12. `certs_cnf` — where openssl.cnf is, its sections, -extensions, openssl ca's [CA_default] · Config Cobra
13. `certs_revoke` — revoke, CRLs, crl_check, OCSP's end, short lifetimes · Revoked Reindeer

### CI/CD

1. `pipeline` — stages, needs, rules, secrets · Indent Imp, Stage Specter, Needs Newt, Secret Sprite,
   Manual Mole

### AI tools

No fights (owner): these lessons pass with right answers to their own questions (`answered ID N`), in
the adventure or in the quiz at the end of the lesson.

1. `ai_context` — what the model sees, tokens, long chats, CLAUDE.md and AGENTS.md, advice versus
   enforced rules
2. `ai_plan` — ask for a plan, review it, step by step, check the diff and the tests

## Known gaps

- **systemd** and **Rust** stop after one lesson: next steps would be timers and journalctl filters,
  ownership and borrowing, each with fights.
- **Bash** has no fights yet for scripts, loops and quotes; **Linux** none for users, permissions,
  disk, archives and network (their achievements master those lessons).
