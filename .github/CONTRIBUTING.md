# Contributing

Ideas, bug reports and new challenges are welcome.

## New security challenge

Open an issue with the *Security challenge idea* template, or a pull request:

1. Add a `Challenge` to `bashou/challenges/security.py` (look at the others): a `setup` that writes
   random, harmless data into the arena folder and returns the answer, a task, and two hints.
2. Add its reference solution to `SOLUTIONS` in `tests/test_fight.py`, then run `python3 -m unittest`.
3. Run `python3 -m bashou.i18n` so its texts go into the translation catalogs.

Rules:

- **Write your own.** Don't copy tasks from CTFs or other sites: take the idea, write a new story and data.
- **Harmless.** Everything stays inside the arena folder. No network, no real system files, nothing
  that runs as root.
- **Standard library only**, no `shell=True` or `eval` (a test checks this).
- Beginner-friendly: the task says what to find, the second hint shows a command that works.
