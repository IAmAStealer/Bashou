# Bash style: at the prompt and in a script

Bashou teaches bash two ways, and every piece of bash we show belongs to one of them:

- **At the prompt** (skill `bash`): typed once, read on the screen, fixed right away. Speed and
  looking around matter, and you see the result before it can hurt.
- **In a script** (skill `script`): runs unattended, later, on file names and failures nobody
  planned for. Reliability matters: a habit that is fine at the prompt can be a bug here.

What both share (how the shell reads a line: quotes, expansion, exit status) is taught once, in
the shared lessons. This file is the checklist for every bash sample in Bashou: lesson pages,
adventure questions, fight tasks, hints and starter files, project templates, and our own shell
code. The `bash-judge` agent (`.claude/agents/bash-judge.md`) applies it after each change.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (to show the mistake)
is marked ✘ and followed by the right form. In a question, wrong choices may be wrong on purpose,
but the right answer and its explanation must follow the rules of their mode.

## Both modes

| Id | Rule | Why |
|---|---|---|
| B1 | Quote expansions: `"$var"`, `"$(cmd)"`, `"${list[@]}"`. Leaving quotes out needs a reason (assignment, inside `[[ ]]` on the left, inside `(( ))`), and a sample that teaches should not rely on it. | Unquoted values are split at spaces and expanded as globs. |
| B2 | Say which shell when bash and zsh differ (splitting, unmatched globs, array indexes). Never show zsh behavior as bash. | Players type in zsh, scripts run in bash. |
| B3 | Facts are exact: exit statuses, options, messages. Name GNU-only forms: `sed -i` (BSD needs `sed -i ''`), `date -d`, `grep -P`, `readlink -f`, `find -printf`, `stat -c`. | Bashou runs on Linux and macOS. |
| B4 | `$( )`, not backticks. Backticks only to recognise them in old code. | Nests without backslashes. |
| B5 | Single quotes around programs with their own syntax: awk, sed, regexes, find patterns. | The shell leaves `$`, `*` and `[ ]` alone. |
| B6 | Never `curl … \| bash`, a password in argv or `-pSecret`, or `eval` on outside data, unless it's the ✘ example. | Security habits are taught by every sample. |

## At the prompt

These are fine at the prompt. When a script lesson or fight sits next to them, say they stop
being fine there.

| Id | Allowed at the prompt | In a script instead |
|---|---|---|
| P1 | `ls`, `ls \| wc -l`, `ls \| grep x` to look around | globs and arrays (S6) |
| P2 | `echo` to show text | `printf` for data (S5) |
| P3 | `cat file \| cmd` | `cmd file` or `cmd < file` |
| P4 | Look first, then act: `ls *.log` then `rm *.log`; `rm -i` | checks in code: `[[ -e $f ]]`, nullglob, `--` |
| P5 | `cd dir` alone: you see the prompt change | `cd dir \|\| exit` (S2) |
| P6 | aliases, `!!`, history, Ctrl+R | no aliases in scripts: functions |
| P7 | A one-line loop: `for f in *.JPG; do mv "$f" "${f%.JPG}.jpg"; done` (still quoted: B1) | `mv -- "$f" …`, nullglob (S6) |

## In a script

Target: bash 4.4 or newer, the same as Bashou itself. macOS's `/bin/bash` is 3.2: the script lesson
says so, and Mac players install a newer one with `brew install bash`.

| Id | Rule | Why |
|---|---|---|
| S1 | First line `#!/usr/bin/env bash`. Bash features need bash: never under `#!/bin/sh`. | `/bin/bash` on a Mac is 3.2; `sh` is often dash. |
| S2 | Check every failure that matters, in the code: `cmd \|\| die "…"`, `if ! cmd; then`. Always `cd dir \|\| exit 1`. | A script doesn't stop by itself, and the next lines work on a broken state. |
| S3 | Errors go to stderr (`>&2`) and end with a non-zero exit status. Usage errors: status 2. | Callers, cron and pipes tell success from failure by the status. |
| S4 | `set -e`, `set -u`, `set -o pipefail` are never shown as enough, or as "the" fix. When shown, name their holes: `set -e` is off inside `if`, `while`, `!`, `&&`/`\|\|` and in functions called there; `((n++))` with n=0 exits; `local`/`export`/`readonly x=$(cmd)` hide cmd's failure; with pipefail, `cmd \| head` can fail with 141 (SIGPIPE). | It's a safety net with holes. Readers trust it and stop checking. |
| S5 | `local out; out=$(cmd) \|\| die …`: declare first, assign apart, when the status matters. Same for `export` and `readonly`. | The builtin's own status (0) replaces cmd's. |
| S6 | `printf '%s\n' "$x"` for data; `echo` only for fixed text. | `echo` changes values like `-n`, `-e` or backslashes. |
| S7 | Files: globs, never `ls` output. `--` or `./*` before names (a file can be called `-rf`). Handle no match: `shopt -s nullglob`, or `[[ -e $f ]] \|\| continue`. Trees: `find … -exec cmd {} +`, `-print0 \| xargs -0`, or `while IFS= read -r -d '' f`. | Names may hold spaces, newlines, leading dashes; a glob that matches nothing stays as the pattern. |
| S8 | Lines: `while IFS= read -r line; do …; done < file`. A command inside that reads stdin (ssh, ffmpeg) gets `< /dev/null` (or `ssh -n`). Never `for line in $(cat file)`. | `read` without them trims spaces and eats backslashes; ssh swallows the rest of the file. |
| S9 | Tests: `[[ ]]` in bash, `(( ))` for numbers. Quote the right side of `==` in `[[ ]]` to compare as text. Check a number is a number before `-gt` or `(( ))`. | `[ ]` breaks on empty values; an unquoted right side is a pattern. |
| S10 | A list of arguments lives in an array: `args=(-v --name "$n")`, `cmd "${args[@]}"`. Pass arguments on with `"$@"`, never `$*` or a string. | A string can't hold a name with a space. |
| S11 | Temp files: `tmp=$(mktemp) \|\| exit 1` and `trap 'rm -f -- "$tmp"' EXIT`. Never a fixed `/tmp/name`. | Cleaned up on every exit; nobody can plant the name first. |
| S12 | A variable used in `rm -r` is guarded: `rm -rf -- "${dir:?}/"`. | An empty variable would make it `rm -rf /`. |
| S13 | Lowercase names for the script's own variables; UPPERCASE is for the environment (`PATH`, `HOME`). | No clash with what programs read. |
| S14 | Arguments are checked and the script prints a usage line: `(( $# == 1 )) \|\| usage`, where usage() prints `usage: ${0##*/} FILE` on stderr and exits 2 (die exits 1). | The first bug of every script is being run the wrong way. |
| S15 | `command -v`, not `which`; `$(( ))`, not `expr`; `name() { … }`, without the `function` keyword. | Builtins, same in every bash. |
| S16 | `bash -n` passes, and ShellCheck is clean. Each `# shellcheck disable=` says why on the same line. | The tests run both on our script samples. |

## The script template

Every script fight and project starts from this file (`bashou/challenges/template.sh`), and adds only the habit it teaches. The template
has no `set -e`: S4 is its own lesson, where the player chooses it knowingly.

```bash
#!/usr/bin/env bash
# What it does, in one line.
# Usage: name.sh FILE...

die() { printf '%s: %s\n' "${0##*/}" "$*" >&2; exit 1; }

main() {
  if (( $# < 1 )); then
    printf 'usage: %s FILE...\n' "${0##*/}" >&2
    exit 2
  fi
  local f
  for f in "$@"; do
    [[ -f $f ]] || die "not a file: $f"
    # your step here
  done
}

main "$@"
```

## Our own shell code

`bashou.bash`, `bashou/*.bash` and the tools follow the script rules, except S1 (they are sourced
into your shell, not run) and S14. They run at every prompt, so they also use builtins only where
they can: no fork per command.

## References

- Greg's wiki: [BashPitfalls](https://mywiki.wooledge.org/BashPitfalls),
  [BashFAQ](https://mywiki.wooledge.org/BashFAQ) (105: why `set -e` doesn't do what you expect),
  [BashGuide](https://mywiki.wooledge.org/BashGuide).
- The [bash manual](https://www.gnu.org/software/bash/manual/bash.html) and `help set`.
- [ShellCheck's wiki](https://www.shellcheck.net/wiki/): one page per warning, with the why.
