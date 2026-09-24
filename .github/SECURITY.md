# Security

Found a security problem in Bashou? Please report it privately with GitHub's
[private vulnerability reporting](https://github.com/IAmAStealer/Bashou/security/advisories/new)
instead of opening a public issue.

What the CI checks on every push, and how releases are made: see
[doc/GUIDE.md](../doc/GUIDE.md#releases-and-security-checks).

## What Bashou touches

Bashou runs as you, with your rights, and never asks for more: it never runs `sudo` (it only prints
install commands for you to run), and nothing of it is setuid. The package's install scripts, run as
root by apt or dnf, only byte-compile and clean `/usr/share/bashou`.

It writes only to:

- `~/.local/share/bashou` (your progress, and the events file of each terminal: what you type, for your
  pet) and `~/.cache/bashou`, both private to you (700; the events files 600). Events of closed
  terminals are removed.
- a private temporary folder for each fight or chest (`mktemp`, 700), removed when you leave it;
- `~/.bashrc`, one line, only when you run `bashou setup`;
- its own folder, only for a git install you update with `bashou update` (release tags only).

What you do in a fight runs as you, in its folder. Bashou's own checks stay contained: the SQL fights run
your SQL on throwaway copies that can only change rows (no `ATTACH`, no `VACUUM INTO`), and the gpg and
pass fights use their own practice key and store, never your `~/.gnupg` or `~/.password-store`.
