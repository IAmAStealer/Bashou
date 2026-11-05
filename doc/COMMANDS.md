# What you can do

**English** · [Français](COMMANDS.fr.md)

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
| `bashou adventure` | A walk through 13 topics with 503 questions about what goes wrong and what to check first, bosses and chests |
| `bashou share` | A QR code: your phone draws a banner of your pet and your progress, to send anywhere |

## Fights

A command that works with the right tool hits the enemy. Only a wrong `answer` costs a heart, so try things freely.

| Fight | What you do |
|---|---|
| Code | Fix a small broken Python, C or Rust file |
| Script | Fix a bash script; it must then survive Bashou's tricky files |
| Packages | Ask your machine with `apt`, `dpkg` or `rpm`, or fix a repository file |
| CI/CD | Fix a GitHub Actions or GitLab CI file |
| SQL | Query and fix an SQLite database |
| Secrets | Practice `gpg` and `pass` with their own key and store, never yours |
| Network | Read addresses, listeners and saved captures; nothing leaves your machine |

Beaten fights come back after 1, 7 and 30 days, so what you learned stays.
In a fight, `lesson` opens the lesson that explains it.

## Play on two computers

```bash
bashou export                           # writes bashou-save-DATE.txt here
bashou import bashou-save-DATE.txt      # on the other computer, same Bashou version
```

For each thing, Bashou keeps the best of the two computers. The file holds no commands, tool counts or dates;
`bashou export --full` carries everything.

## Your data stays on your machine

Bashou collects nothing: no account, no telemetry, no ads.

- It reads your commands only to count tools, and keeps the counts in `~/.local/share/bashou`.
- It only asks the internet whether a new version is out, once a day. `bashou config updates off` stops that; apt and dnf installs never ask.

Bashou is a small side project, made with spare AI tokens by someone who likes teaching. There is nothing to sell.

`bashou share` shows what the banner holds before the QR code: no commands, files, machine names or dates.
