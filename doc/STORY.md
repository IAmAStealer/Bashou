# How Bashou appeared

It started as **Zenos**, a tiny breathing companion for the terminal: a cat in the corner that
breathed slowly, loaded from `~/.bashrc`, and stayed there while you worked.

Then came an idea: what if that cat could teach bash? Pets could be unlocked by running commands,
trying new tools (`find`, `awk`, `ps`, `strace`…) and writing more complex lines. Threats would show
up now and then, and you would fight them with real commands in a sandbox. The project was renamed
**Bashou** (bash + « chou », French for "cute").

## Made with AI, for responsible use

The Python version is made with AI ([Claude Code](https://claude.com/claude-code)): the owner gives
the ideas, playtests and reports bugs; Claude writes the code, the pixel art, the tests and the docs.

The point is learning, so you can do it too. Bashou teaches you the shell instead of doing it for
you, and the project is built the same way: AI is a tool here, not a requirement. Some things are
made by AI, but nothing *has to* be: every pet, challenge or line of code can be written by hand,
and contributions made without AI are just as welcome.

Expect rough edges: it's a playground to find out whether the idea is fun.

## What's next: a single Rust binary

The goal is to rewrite Bashou as **one Rust binary**. The owner does this migration by hand, without AI:

- install and uninstall itself (the `~/.bashrc` line included), and keep your progress;
- update itself from GitHub releases, and check the signature of what it downloads;
- start faster and use less memory than the Python daemon.

The Python version stays the reference for the behavior until then.
