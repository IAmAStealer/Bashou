# Packages style: apt and dnf, without breaking the system

Bashou teaches packages on the two families players run: Debian and its children (apt, dpkg) and Red
Hat's (dnf, rpm: Rocky, Alma, Fedora). The ideas are the same (a signed repository, dependencies, a
local database), the commands and files differ.

This file is the checklist for every package sample in Bashou: the lessons `packages` and `repos`,
the debian and rocky adventure questions, the fights of `bashou/challenges/packages.py` and
`repos.py`, their hints and files. The `packages-judge` agent (`.claude/agents/packages-judge.md`)
applies it after each change, and `tests/test_packages_style.py` checks the text players read.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (a wrong choice, the
mistake a fight shows) is marked ✘ and followed by the right form. The right answer, its explanation
and the hints must follow the rules.

Facts are checked by running the command (here, read-only: `apt policy`, `dpkg -S`, `rpm -qf`,
`dnf --assumeno`) or against the man pages and the distributions' own docs, never from memory.

| Id | Rule | Why | Source |
|---|---|---|---|
| P1 | `apt` at the prompt; `apt-get` and `apt-cache` in scripts. | apt's output and behavior may change between versions; apt-get keeps them. | [apt(8)](https://manpages.debian.org/trixie/apt/apt.8.en.html) |
| P2 | `apt update` only refreshes the lists; `upgrade` never removes a package, `full-upgrade` may. `dnf upgrade` refreshes its metadata itself when it is old. Each command is named for what it does. | "update" is the word beginners mix up. | [apt(8)](https://manpages.debian.org/trixie/apt/apt.8.en.html), [dnf(8)](https://dnf.readthedocs.io/en/latest/command_ref.html) |
| P3 | A third-party repository's key is a file in `/etc/apt/keyrings/` (or `/usr/share/keyrings/` when a package ships it), named by `Signed-By` in that repository's entry. Never `apt-key` (gone in Debian 13), never `/etc/apt/trusted.gpg.d/`, never `[trusted=yes]` or `--allow-unauthenticated`. | A key in the global store can sign packages for every repository. | [Debian wiki: third-party repositories](https://wiki.debian.org/DebianRepository/UseThirdParty), [sources.list(5)](https://manpages.debian.org/trixie/apt/sources.list.5.en.html) |
| P4 | Software comes from the distribution's repositories first, then backports (Debian), EPEL (Rocky), Flatpak. Never `curl … \| sudo bash`, never a random `.deb` or `.rpm` from a website, never another distribution's repository (Ubuntu PPAs on Debian). | It bypasses the signature and the security updates, and can break the system. | [Debian wiki: DontBreakDebian](https://wiki.debian.org/DontBreakDebian) |
| P5 | Don't mix Debian releases (stable with testing or unstable): a "FrankenDebian" breaks on the next upgrade. | Newer libraries pulled in by one package. | [Debian wiki: DontBreakDebian](https://wiki.debian.org/DontBreakDebian#Don.27t_make_a_FrankenDebian) |
| P6 | Repository files by system: Debian 13 `/etc/apt/sources.list.d/debian.sources` (deb822 format), Debian 12 `/etc/apt/sources.list` (one-line format, still read; an upgraded Debian 13 keeps it until `apt modernize-sources`); Rocky `/etc/yum.repos.d/*.repo`, one `[id]` per repository, ids in lower case (`baseos`, `appstream`, `crb`). | Players look for the file their system has. | [sources.list(5)](https://manpages.debian.org/trixie/apt/sources.list.5.en.html), [Debian wiki: SourcesList](https://wiki.debian.org/SourcesList), [Rocky: software management](https://docs.rockylinux.org/books/admin_guide/13-softwares/) |
| P7 | Ask before you change: `apt policy`, `apt-get --simulate` (`-s`), `dnf --assumeno`, `dnf repoquery`; read the list of packages a removal takes with it. | A removal can take half the desktop with it. | [apt-get(8)](https://manpages.debian.org/trixie/apt/apt-get.8.en.html), [DontBreakDebian](https://wiki.debian.org/DontBreakDebian), [dnf(8)](https://dnf.readthedocs.io/en/latest/command_ref.html) |
| P8 | Rocky: `dnf`; `yum` on Rocky 8 and later runs dnf (DNF is YUM's successor). `gpgcheck=1` stays on (dnf's own default is 0: the distribution's files set it). EPEL: `dnf install epel-release`, CRB with `dnf config-manager --set-enabled crb`. Rocky 10 dropped modules (`dnf module`). | Old yum tutorials, and gpgcheck=0 "fixes". | [Rocky: software management](https://docs.rockylinux.org/books/admin_guide/13-softwares/), [Rocky: DNF and CRB](https://docs.rockylinux.org/guides/package_management/dnf_package_manager/), [dnf.conf(5)](https://dnf.readthedocs.io/en/latest/conf_ref.html) |
| P9 | Low level vs high level: `dpkg`/`rpm` read and change the local database and single files; `apt`/`dnf` talk to repositories and resolve dependencies. Installing a downloaded file goes through apt or dnf (`apt install ./file.deb`, `dnf install ./file.rpm`) so dependencies come too. | `dpkg -i` leaves missing dependencies. | [dpkg(1)](https://manpages.debian.org/trixie/dpkg/dpkg.1.en.html), [rpm(8)](https://rpm-software-management.github.io/rpm/man/rpm.8.html), [apt(8)](https://manpages.debian.org/trixie/apt/apt.8.en.html) |
| P10 | Manual vs auto: `apt autoremove` removes only auto-installed packages nothing needs; `apt-mark manual` keeps one. dnf: `dnf autoremove`, `dnf mark install name` (dnf 4; dnf5 says `dnf mark user`). | Autoremove removing "my" library. | [apt-mark(8)](https://manpages.debian.org/trixie/apt/apt-mark.8.en.html), [dnf(8)](https://dnf.readthedocs.io/en/latest/command_ref.html) |
| P11 | Version strings are quoted whole: Debian `[epoch:]upstream-revision` (`1:2.39.5-0+deb12u2`), rpm `name-version-release.arch` (`bash-5.1.8-9.el9.x86_64`). | Comparing versions by hand goes wrong. | [deb-version(7)](https://manpages.debian.org/trixie/dpkg-dev/deb-version.7.en.html), [rpm(8)](https://rpm-software-management.github.io/rpm/man/rpm.8.html) |

## Versions players run

| Where | apt / dnf | Sources file |
|---|---|---|
| Debian 12 | apt 2.6 | `/etc/apt/sources.list` |
| Debian 13 | apt 3.0 (no apt-key) | `/etc/apt/sources.list.d/debian.sources` |
| Ubuntu 24.04 | apt 2.7 | `/etc/apt/sources.list.d/ubuntu.sources` |
| Rocky 9 | dnf 4 | `/etc/yum.repos.d/rocky*.repo` |
| Rocky 10 | dnf 4, no modules | `/etc/yum.repos.d/rocky*.repo` |
