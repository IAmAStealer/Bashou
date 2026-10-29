# Logic style: yes, no, and, or, not

Bashou teaches logic through exit statuses: every command answers yes (0) or no, `if` picks a road,
`!`, `&&` and `||` combine answers. Then the same three words in Python and C. A wrong truth table or a
test that only seems to work teaches the wrong reflex for every language after.

This file is the checklist for every logic sample in Bashou: the lesson `logic`, the logic adventure
questions, the fights of `bashou/challenges/logic.py`, their hints and files, and conditions shown in
other lessons. The `logic-judge` agent (`.claude/agents/logic-judge.md`) applies it after each change,
and `tests/test_logic_style.py` checks the text players read.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (a wrong choice, the bug
a fight asks to fix) is marked ✘ and followed by the right form. The right answer, its explanation
and the hints must follow the rules.

Facts are checked by running (bash, `sh` = dash on Debian, python3, gcc) or against POSIX, the bash
manual, the Python docs and cppreference, never from memory.

| Id | Rule | Why | Source |
|---|---|---|---|
| L1 | Exit status 0 is yes (success), anything else is no. `test` and `[` answer 0 true, 1 false, more than 1 an error; grep 0 found, 1 not found, 2 an error. An error is not a "no": say which one the code sees. | `if grep` takes an unreadable file for "not found". | [POSIX test](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html), [POSIX grep](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/grep.html) |
| L2 | `[` is a command: spaces around `[`, `]` and each operator; variables in double quotes. | `[-f x]` and an empty variable break the test. | [POSIX test](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) |
| L3 | Numbers with `-eq -ne -lt -le -gt -ge`, text with `=` and `!=`. `<` and `>` inside `[ ]` are redirections. | `[ 10 < 9 ]` creates a file named 9. | [POSIX test](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html), [Bash manual: conditional expressions](https://www.gnu.org/software/bash/manual/html_node/Bash-Conditional-Expressions.html) |
| L4 | Inside `[ ]`, text equality is `=`. `==` belongs to bash's `[[ ]]` (where an unquoted right side is a pattern). | `[ a == b ]` fails in sh (dash). | [POSIX test](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html), [Bash manual: [[ ]]](https://www.gnu.org/software/bash/manual/html_node/Conditional-Constructs.html) |
| L5 | Tests are joined with `&&` and `\|\|` between commands: `[ -f a ] && [ -d b ]`. Not `-a`/`-o` inside `[ ]`: POSIX removed them (2024). | They are ambiguous with some values. | [POSIX test, application usage](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) |
| L6 | `a && b \|\| c` is not if/then/else: `c` also runs when `b` fails. Show `if` when both roads matter. | The classic shortcut that runs both. | [Bash manual: lists](https://www.gnu.org/software/bash/manual/html_node/Lists.html) |
| L7 | Short-circuit is stated exactly: `a && b` runs b only if a succeeded, `a \|\| b` only if a failed; `&&` and `\|\|` have equal precedence and group left to right in bash (unlike most languages, where `and` binds tighter). | `a \|\| b && c` reads differently in bash and Python. | [Bash manual: lists](https://www.gnu.org/software/bash/manual/html_node/Lists.html), [Python: operator precedence](https://docs.python.org/3/reference/expressions.html#operator-precedence) |
| L8 | `!` needs a space after it (`! grep`, `[ ! -f x ]`); at the prompt, `!` followed by text is history expansion in interactive bash. | `!grep` runs the last grep command. | [Bash manual: history expansion](https://www.gnu.org/software/bash/manual/html_node/History-Interaction.html), [Bash manual: pipelines](https://www.gnu.org/software/bash/manual/html_node/Pipelines.html) |
| L9 | Truth in other languages: Python `and or not`, with falsy values (`0`, `""`, `[]`, `None`) and `and`/`or` returning one of their operands; C `&& \|\| !`, 0 false and any other value true, results 0 or 1. Bash's 0 = yes is said as the exception. | Carrying bash's 0 into Python or C. | [Python: truth value testing](https://docs.python.org/3/library/stdtypes.html#truth-value-testing), [cppreference: logical operators](https://en.cppreference.com/w/c/language/operator_logical) |
| L10 | Truth tables and De Morgan (`not (a and b)` = `not a or not b`) are checked by running every case, not by reasoning. | One wrong row teaches the wrong law. | [Python: boolean operations](https://docs.python.org/3/reference/expressions.html#boolean-operations) |
| L11 | A guard reads its input as data: `grep -qxF -- "$name"` (whole line, fixed text, `--` before a value that may start with `-`). | A name like `.*` or `-v` must not change what the guard checks. | [POSIX grep](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/grep.html), [POSIX utility syntax guideline 10](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap12.html#tag_12_02) |
