# Security challenges for Bashou

`bashou security` has small investigations: something happened on a (fake) machine, and the
player uses the shell to find out what. New challenges are welcome, as an idea (issue) or as code
(pull request).

## A good challenge

- **One question, one answer**: a word, an IP, a file name, a number.
- **Something real admins do**: reading logs, finding a file, spotting a bad permission, decoding
  something, following a suspicious process…
- **Beginner-friendly**: the task says what to look for; the first hint gives the idea, the second
  one shows a command that works.
- **Random every time**: names, IPs and numbers change, so the answer can't be copied.
- **A trap for the lazy way** is welcome (e.g. the busiest IP in the log is the admin, not the
  attacker), as long as the task is fair.

## Rules

- **Write your own.** Take ideas from CTFs or courses, but write a new story and new data: don't
  copy tasks, texts or files.
- **Harmless.** Everything happens in the sandbox folder Bashou creates. No network, no real system
  files, nothing that needs root, nothing that runs in the background after the challenge (or
  stop it in `cleanup`).
- **Standard library only**, no `shell=True` or `eval` (a test checks this).

## Idea only?

Open an issue with the *Security challenge idea* template: the story, the files, the answer, a
command that solves it.

## Code

Challenges live in `bashou/challenges/security.py`. A challenge is a `setup` function and a
`Challenge`:

```python
def leak_setup(work, rng):
    """Write the sandbox files into `work` (a pathlib.Path). Return what the check needs."""
    token = f"tok_{rng.randrange(16 ** 8):08x}"
    (work / "app.env").write_text(f"DEBUG=true\nAPI_TOKEN={token}\n")
    return {"answer": token}


LEAK = Challenge(
    id="env_leak", pet="", tools=(), threat="Leaked token", level=1, kind="security",
    task="A config file of this app leaks a secret token. What is it?",
    hints=["Config files often end in .env or .conf. grep can search for TOKEN.",
           "Try: grep -r TOKEN ."],
    setup=leak_setup, requires=["grep"],
)
```

- `level`: 1 easy, 2 medium, 3 hard. `requires`: the programs it needs (it's hidden if they're missing).
- The answer is compared as text. For answers that can be written several ways (a path with or
  without `./`), add a `verify(work, meta, value)` function (see `recent_verify`).
- `threat` is the challenge's title in the list.

Then:

1. Add it to `SECURITY` at the end of the file, and its number to `_bashou_security` in `bashou.bash`.
2. Add its reference solution to `SOLUTIONS` in `tests/test_fight.py`: a command that prints the
   answer.
3. Run `python3 -m bashou.i18n` (puts its texts in the translation catalogs) and `python3 -m unittest`.
4. Try it for real: `bashou security <number>`.
