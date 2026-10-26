# Python style: at the prompt and in a program

Bashou teaches Python 3 two ways, and every piece of Python we show belongs to one of them:

- **At the prompt**: the `python3` prompt (`>>>`), or a one-liner `python3 -c '…'` typed in the
  shell. Typed once, read on the screen: you see the result before it matters.
- **In a program**: a `.py` file run with `python3 file.py`, a fight's starter file, a project. It runs
  later, on data nobody checked, often from cron or another program that only sees its exit code.

This file is the checklist for every Python sample in Bashou: lesson pages (`py_*`), adventure
questions (`python.json`, and Python in other topics), fight tasks, hints and starter files
(`bashou/challenges/code.py` and the other fights that write `.py` files), project steps
(`bashou/project/*/python_*.json`). The `python-judge` agent (`.claude/agents/python-judge.md`)
applies it after each change, and `tests/test_python_style.py` parses every Python file a fight
writes with the grammar of Python 3.9 and checks the text never teaches what the rules forbid.

Each rule has an id, used in reviews, and an official source: the Python docs (docs.python.org), a
PEP, or the distribution's own page. A sample that breaks a rule on purpose (the bug a fight asks to
fix, the wrong choice of a question) is fine; the right answer, its explanation and the fixed file
must follow the rules.

Facts are checked, never taken from memory: run the code with the oldest Python we support (3.9,
see Versions), or read the docs page of that version.

## Both modes

| Id | Rule | Why | Source |
|---|---|---|---|
| Y1 | The command is `python3`, never `python`. | On Debian, Rocky and macOS `python` may be missing, or another Python. | [PEP 394](https://peps.python.org/pep-0394/) |
| Y2 | Data is read with a parser (`json.load`, `csv`, `int()`, `ast.literal_eval`), never `eval` or `exec`. | `eval` runs the text as code: whoever can edit the file runs anything. | [eval](https://docs.python.org/3/library/functions.html#eval), [ast.literal_eval](https://docs.python.org/3/library/ast.html#ast.literal_eval) |
| Y3 | `None` is tested with `is None` / `is not None`; a true/false value with `if x:`, never `== True`. | `==` can be redefined by a class; `is` asks "this very object". | [PEP 8, programming recommendations](https://peps.python.org/pep-0008/#programming-recommendations) |
| Y4 | Blocks are indented with 4 spaces, never tabs. | Mixing tabs and spaces is a `TabError`; 4 spaces is the standard every editor follows. | [PEP 8, indentation](https://peps.python.org/pep-0008/#indentation), [lexical analysis, indentation](https://docs.python.org/3/reference/lexical_analysis.html#indentation) |
| Y5 | Names: `snake_case` for functions and variables, `CapWords` for classes, `UPPER_CASE` for constants. No `l`, `O` or `I` alone. | The convention every Python reader expects. | [PEP 8, naming](https://peps.python.org/pep-0008/#naming-conventions) |
| Y6 | Text is built with f-strings: `f"{name} has {n} hosts"`. Not `+` with `str()`, not `%`. | Shorter, and the value sits where it shows. | [f-strings](https://docs.python.org/3/reference/lexical_analysis.html#f-strings), [PEP 498](https://peps.python.org/pep-0498/) |
| Y7 | An exception is caught by its name (`except FileNotFoundError:`), around the one line that can raise it. Never a bare `except:`, never `except Exception: pass`. | A bare `except` also catches Ctrl+C (`KeyboardInterrupt`) and hides real bugs. | [PEP 8, programming recommendations](https://peps.python.org/pep-0008/#programming-recommendations), [tutorial: errors](https://docs.python.org/3/tutorial/errors.html#handling-exceptions) |
| Y8 | No mutable default argument: `def add(x, seen=None):` then `if seen is None: seen = []`, never `seen=[]`. | The default is made once, when `def` runs: every call shares the same list. | [tutorial: default argument values](https://docs.python.org/3/tutorial/controlflow.html#default-argument-values) |
| Y9 | Code runs on Python 3.9. A feature newer than 3.9 says what it needs ("needs Python 3.10+"), and never sits in a fight or a starter file. See Versions. | Rocky 9 and macOS's own `python3` are 3.9. | [What's New](https://docs.python.org/3/whatsnew/index.html) |
| Y10 | Comparing floats for equality uses `math.isclose`, or the sample says why `0.1 + 0.2 != 0.3`. | Binary floats can't hold most decimals exactly. | [tutorial: floating point](https://docs.python.org/3/tutorial/floatingpoint.html), [math.isclose](https://docs.python.org/3/library/math.html#math.isclose) |
| Y11 | A claim about Python's behavior is true for the versions in the table, and checked by running it (`python3 -c`) or in the docs of that version. Never "dicts are unordered" (they keep insertion order since 3.7). | Players run what we say. | [dict](https://docs.python.org/3/library/stdtypes.html#dict) |

## At the prompt

These are fine at the prompt. When a program sits next to them (a lesson about files, a fight's
starter), say they stop being fine there.

| Id | Allowed at the prompt | In a program instead | Source |
|---|---|---|---|
| YP1 | The `>>>` prompt shows a value without `print`. | `print(…)`: a program shows nothing on its own. | [tutorial: interactive mode](https://docs.python.org/3/tutorial/interpreter.html#interactive-mode) |
| YP2 | `exit()` or Ctrl+D (Ctrl+Z, Enter on Windows) leaves the prompt. | `sys.exit(…)`: `exit()` comes from the `site` module, for the prompt only. | [site constants](https://docs.python.org/3/library/constants.html#constants-added-by-the-site-module), [sys.exit](https://docs.python.org/3/library/sys.html#sys.exit) |
| YP3 | `python3 -c '…'`: the code in single quotes, text inside it in double quotes. Several statements on one line with `;`; a block (`for`, `if`) needs a file or real newlines. | a file | [command line: -c](https://docs.python.org/3/using/cmdline.html#cmdoption-c), bash quoting (bash-style B1) |
| YP4 | `python3 -m json.tool file.json` to look at JSON. | `json.load` (Y2) | [json.tool](https://docs.python.org/3/library/json.html#module-json.tool) |
| YP5 | `open(…).read()` without `with`, to peek at a file once. | `with open(…) as fh:` (YC2) | [tutorial: reading and writing files](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files) |

## In a program

| Id | Rule | Why | Source |
|---|---|---|---|
| YC1 | An error goes to stderr and the program exits non-zero: `print(msg, file=sys.stderr)` then `sys.exit(1)`, or `sys.exit(msg)` (prints msg to stderr, exits with 1). | The shell, cron or CI only look at the exit code; 0 says it worked. | [sys.exit](https://docs.python.org/3/library/sys.html#sys.exit), [sys.stderr](https://docs.python.org/3/library/sys.html#sys.stderr) |
| YC2 | A file is opened with `with`, and a text file with `encoding="utf-8"`. Binary files (a PDF, an image) with `"rb"`/`"wb"`. | `with` closes it even on an error; without `encoding` the text codec depends on the machine's locale. | [tutorial: reading and writing files](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files), [open](https://docs.python.org/3/library/functions.html#open), [PEP 597](https://peps.python.org/pep-0597/) |
| YC3 | Paths are joined with `pathlib.Path` (`base / name`) or `os.path.join`, never with `+ "/" +`. | Works on every OS, and with names holding odd characters. | [pathlib](https://docs.python.org/3/library/pathlib.html) |
| YC4 | Another program runs with `subprocess.run(["cmd", arg], check=True)`: a list, no `shell=True` with data inside, no `os.system`. | With a shell, a `;` in the data runs a second command: shell injection. | [subprocess: security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations), [subprocess.run](https://docs.python.org/3/library/subprocess.html#subprocess.run) |
| YC5 | A file that can be imported (by a test, by Bashou's check) keeps its work in functions and runs it under `if __name__ == "__main__":`. | Importing the file must not run the program. | [`__main__`](https://docs.python.org/3/library/__main__.html) |
| YC6 | Arguments: `sys.argv` for one or two, `argparse` beyond. A missing or bad argument gets a usage message on stderr and a non-zero exit. | `argparse` writes the usage and `--help` for you. | [argparse tutorial](https://docs.python.org/3/howto/argparse.html), [sys.argv](https://docs.python.org/3/library/sys.html#sys.argv) |
| YC7 | Values go into SQL as parameters (`?`), never f-strings: see sql-style QC1. | SQL injection. | [sqlite3: placeholders](https://docs.python.org/3/library/sqlite3.html#sqlite3-placeholders) |
| YC8 | Secrets come from the environment (`os.environ["TOKEN"]`) or a file outside the repo, never written in the code. | Code gets shared, pushed and printed. | [os.environ](https://docs.python.org/3/library/os.html#os.environ) |
| YC9 | Fights and starter files use the standard library only. A project that needs a package installs it in a virtual environment: `python3 -m venv .venv`, then `.venv/bin/pip install …` (or `source .venv/bin/activate` first). Never `sudo pip`, never `--break-system-packages`. | Debian 12 and newer refuse `pip install` outside a venv (externally managed); sudo pip breaks the system's own Python tools. | [venv](https://docs.python.org/3/library/venv.html), [installing packages](https://packaging.python.org/en/latest/tutorials/installing-packages/), [PEP 668](https://peps.python.org/pep-0668/) |
| YC10 | A loop that waits or retries is bounded: a number of tries and a `time.sleep` between them. | An endless retry hangs cron jobs and hammers the other side. | [time.sleep](https://docs.python.org/3/library/time.html#time.sleep) |
| YC11 | A script run as `./name.py` starts with `#!/usr/bin/env python3` and is made executable (`chmod +x`). | The kernel reads the first line to know what runs the file. | [using Python on Unix: scripts](https://docs.python.org/3/using/unix.html#miscellaneous), [PEP 394](https://peps.python.org/pep-0394/) |

## Versions

What CI and players run. Fights, starter files and checks use only what 3.9 has; a newer feature is
taught in text with "needs Python 3.x+".

| System | `python3` | Source |
|---|---|---|
| Rocky 9 | 3.9 | [RHEL 9: installing and using Python](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/installing_and_using_dynamic_programming_languages/assembly_introduction-to-python_installing-and-using-dynamic-programming-languages) |
| Debian 12 | 3.11 | [packages.debian.org: python3](https://packages.debian.org/bookworm/python3) |
| macOS (Command Line Tools) | 3.9 | `/usr/bin/python3 --version` in our macOS CI job: [Python 3.9.6, 2026-10-25](https://github.com/IAmAStealer/Bashou/actions/runs/40192957609/job/121167692140) |
| CI | 3.9 and 3.13 | `.github/workflows/ci.yml` |

| Feature | Needs | Source |
|---|---|---|
| `str.removeprefix`, `dict \| dict`, `list[int]` | 3.9 | [What's New 3.9](https://docs.python.org/3/whatsnew/3.9.html) |
| `match`, `int \| None` in annotations at run time, `with (a, b):` | 3.10 | [What's New 3.10](https://docs.python.org/3/whatsnew/3.10.html) |
| `tomllib`, `except*`, `ExceptionGroup` | 3.11 | [What's New 3.11](https://docs.python.org/3/whatsnew/3.11.html) |
| `type` statement, same quotes nested in an f-string, `itertools.batched` | 3.12 | [What's New 3.12](https://docs.python.org/3/whatsnew/3.12.html) |
