# How Bashou appeared

It started as **Zenos**, a tiny breathing companion for the terminal: a cat in the corner that
breathed slowly, loaded from `~/.bashrc`, and stayed there while you worked.

Then came an idea: what if that cat could teach bash? Pets could be unlocked by running commands,
trying new tools (`find`, `awk`, `ps`, `strace`…) and writing more complex lines. Threats would show
up now and then, and you would fight them with real commands in a sandbox. The project was renamed
**Bashou** (bash + « chou », French for "cute").

## Fully vibecoded

This version is **100% vibecoded** with [Claude Code](https://claude.com/claude-code), for testing
purposes. The owner gave the ideas, playtested, and reported bugs. Claude wrote the Python code,
the pixel art, the tests and the docs.

Expect rough edges: it's a playground to find out whether the idea is fun.

## What's next: a single Rust binary

The goal is to rewrite Bashou as **one Rust binary**, written by hand this time:

- install and uninstall itself (the `~/.bashrc` line included), and keep your progress;
- update itself from GitHub releases, and check the signature of what it downloads;
- start faster and use less memory than the Python daemon.

The Python version stays the reference for the behavior until then.
