# Linux style: running a Linux system without breaking it

Bashou teaches the system around the shell: users and sudo, permissions, processes and signals,
disk space, services and their logs, the file tree, secrets with gpg and pass. Players then run real
servers, so every habit must hold on the systems they meet (Debian, Ubuntu, Rocky) and every fact
must match the release they run.

This file is the checklist for every Linux sample in Bashou: the lessons `users`, `permissions`,
`processes`, `disk`, `archives`, `services`, `pass` and the system parts of `paths`, the linux and
systemd adventure questions, the fights of `bashou/challenges/system.py`, `security.py` and
`secrets.py`, their hints and files. The `linux-judge` agent (`.claude/agents/linux-judge.md`)
applies it after each change, and `tests/test_linux_style.py` checks the text players read. Shell
syntax itself is bash-judge's; packages are packages-judge's; SSH keys and firewalls are network-judge's.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (a wrong choice, the
mistake a fight shows) is marked ✘ and followed by the right form. The right answer, its explanation
and the hints must follow the rules.

Facts are checked by running the command (read-only: `systemctl cat`, `systemd-analyze`, `stat`,
`id`, `findmnt`, `journalctl`) or against the man pages and the distributions' release notes, never
from memory.

| Id | Rule | Why | Source |
|---|---|---|---|
| LX1 | sudo runs one command as root for a user the sudoers file allows (group `sudo` on Debian and Ubuntu, `wheel` on Rocky). Edit the rules with `visudo` (or a file in `/etc/sudoers.d/` with `visudo -f`), which checks the syntax first. `sudo -l` lists what you may run. | A broken sudoers file locks everyone out of sudo. | [sudoers(5)](https://www.sudo.ws/docs/man/sudoers.man/), [visudo(8)](https://www.sudo.ws/docs/man/visudo.man/) |
| LX2 | Permissions are opened only as far as needed: a secret file is `600` (or `640` for a service's group), a script `755` or `700`. Never `chmod 777` (or `-R 777`) as a fix. On a folder, `x` means entering it. | 777 lets every user and every compromised service change the file. | [POSIX chmod](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html), [inode(7)](https://man7.org/linux/man-pages/man7/inode.7.html) |
| LX3 | setuid (`s` in the owner's x place) runs the program as its owner, root for `passwd`; an unexpected setuid file is a finding (`find / -perm -4000`). setgid on a folder makes new files take its group. | A setuid shell copy is a classic back door. | [inode(7)](https://man7.org/linux/man-pages/man7/inode.7.html), [POSIX chmod](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html) |
| LX4 | Stopping a process: `kill` (SIGTERM) first and a few seconds' wait, `kill -9` (SIGKILL) last, since it can't be caught and leaves no cleanup. Ctrl+C sends SIGINT. Signal numbers are given with their names. | Half-written files and stale locks after a reflex kill -9. | [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html), [kill(1)](https://man7.org/linux/man-pages/man1/kill.1.html) |
| LX5 | Disk space: `df` per filesystem, `du` per folder; a full disk can also be full inodes (`df -i`) or space held by a deleted file still open (`lsof +L1`, freed when the program closes it or restarts). Trim the journal with `journalctl --vacuum-size=`, not by deleting its files. | "I deleted the log and nothing came back." | [df (coreutils)](https://www.gnu.org/software/coreutils/manual/html_node/df-invocation.html), [lsof(8)](https://man7.org/linux/man-pages/man8/lsof.8.html), [journalctl(1)](https://man7.org/linux/man-pages/man1/journalctl.1.html) |
| LX6 | `start` runs a unit now, `enable` at boot, `enable --now` both; `daemon-reload` after changing a unit file. Your own units go in `/etc/systemd/system/`; packaged ones live in `/usr/lib/systemd/system/` and are changed with a drop-in (`systemctl edit name`), never edited in place. `systemctl cat` shows what systemd really uses. | A package upgrade overwrites a packaged unit file. | [systemctl(1)](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html), [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html) |
| LX7 | Unit files: `[Unit]` (Description, After, Wants), `[Service]` (ExecStart with an absolute path, Type, Restart, User), `[Install]` (WantedBy). `After=` only orders; `Wants=`/`Requires=` pull a unit in; waiting for the network takes both `Wants=` and `After=network-online.target`. `Type=simple` (or `exec`) for a program that stays in the foreground, `oneshot` for one that exits. | The unit that starts before the network or "succeeds" too early. | [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html), [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html), [systemd: network-online](https://systemd.io/NETWORK_ONLINE/) |
| LX8 | A service runs as its own user (`User=`, or `DynamicUser=yes`), not root. Its secrets never go in `Environment=` (any user can read them with `systemctl show`): use `LoadCredential=` or an `EnvironmentFile=` readable by root only. | The unit file and its environment are readable by everyone. | [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html), [systemd: credentials](https://systemd.io/CREDENTIALS/) |
| LX9 | Logs: `journalctl -u name` for one service, `-b` this boot, `-f` follow, `-p err` errors only. Text files differ by system: since Debian 12, rsyslog isn't installed by default, so there may be no `/var/log/syslog` or `/var/log/auth.log`; Rocky writes `/var/log/messages` and `/var/log/secure`. Say which system a path belongs to. | Players look for a file their system doesn't have. | [journalctl(1)](https://man7.org/linux/man-pages/man1/journalctl.1.html), [Debian 12 release notes: system logging](https://www.debian.org/releases/bookworm/amd64/release-notes/ch-information.en.html) |
| LX10 | Login history: Debian 13 dropped `last`, `lastb` and `lastlog` (wtmp isn't year-2038 safe); use `journalctl -u ssh`, `lslogins`, or `wtmpdb last` and `lastlog2` from their packages. `last` still works on Debian 12 and Rocky. | A command the player's system no longer has. | [Debian 13 release notes: last, lastb, lastlog](https://www.debian.org/releases/trixie/release-notes/issues.en.html) |
| LX11 | Timers replace cron jobs with `OnCalendar=` (check it with `systemd-analyze calendar`) and `Persistent=true` to catch a run missed while off. A cron job runs with a minimal environment (short PATH, no profile): full paths in scripts. | Works by hand, fails at 3:00. | [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html), [systemd-analyze(1)](https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html), [crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html) |
| LX12 | The file tree: `/etc` configuration, `/var` data that changes (logs, databases), `/run` runtime files in memory, `/usr/local` what you build yourself, `/home` users. `/tmp` is emptied at boot on Debian and Ubuntu and, since Debian 13, is in memory (tmpfs); Rocky keeps it on disk and deletes files older than 10 days: no big files there. | Backups of the wrong folders, a full RAM from /tmp. | [FHS 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html), [tmpfiles.d(5)](https://www.freedesktop.org/software/systemd/man/latest/tmpfiles.d.html), [Debian 13 release notes: /tmp in tmpfs](https://www.debian.org/releases/trixie/release-notes/issues.en.html) |
| LX13 | Changing sshd on a remote server: `sudo sshd -t` before reloading, and keep the current session open until a new login works. `PermitRootLogin no` (or `prohibit-password`) and `PasswordAuthentication no` once keys work. | One typo and nobody can log in. | [sshd(8)](https://man.openbsd.org/sshd), [sshd_config(5)](https://man.openbsd.org/sshd_config) |
| LX14 | `/etc/fstab`: devices by `UUID=`, `nofail` for a disk that may be missing; test with `sudo findmnt --verify` and `sudo mount -a` before rebooting. | A wrong line can stop the boot. | [fstab(5)](https://man7.org/linux/man-pages/man5/fstab.5.html), [findmnt(8)](https://man7.org/linux/man-pages/man8/findmnt.8.html) |
| LX15 | gpg and pass: `gpg -c` encrypts with a passphrase, `gpg -e -r` for a key's owner; a valid signature proves which key signed, so the key's fingerprint is checked from a trusted place. pass keeps one gpg file per secret, locked to the key in `.gpg-id`; a script fetches with `pass show` and stops when it fails. | A signature checked against the attacker's own key. | [GnuPG manual](https://www.gnupg.org/documentation/manuals/gnupg/), [pass](https://www.passwordstore.org/) |

## Versions players run

| Where | systemd | Notes |
|---|---|---|
| Debian 12 | 252 | no rsyslog by default; `last` present |
| Debian 13 | 257 | `/tmp` in tmpfs; no `last`, `lastb`, `lastlog` |
| Ubuntu 24.04 | 255 | rsyslog installed: `/var/log/auth.log` |
| Rocky 9 | 252 | `/var/log/secure`, `/var/log/messages` |
| Rocky 10 | 257 | |
