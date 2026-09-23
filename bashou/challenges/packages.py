"""Package fights (owner, 2026-09-23): ask the real package database of this machine.

They only come on the matching family, read from /etc/os-release (see Challenge.distro): Debian and
its children (Ubuntu…) for dpkg/apt, Red Hat and its rebuilds (Rocky, Alma, Fedora…) for rpm/dnf.
Answers are computed at setup from the same database the player queries.
"""

import os
import subprocess

from . import Challenge

COMMON = ("bash", "coreutils", "grep", "sed", "tar", "gzip", "findutils", "util-linux", "procps", "openssl",
          "curl", "git", "python3", "openssh-client", "less", "diffutils", "passwd", "hostname")
EXTRAS = ("htop", "jq", "tree", "nmap", "ncdu", "tmux", "ripgrep", "lynis", "fail2ban", "rsync", "mtr", "iotop",
          "strace", "tcpdump", "whois", "zstd", "btop", "ranger", "cowsay", "figlet")
DEBIAN = ("debian",)
REDHAT = ("rhel", "fedora", "centos")


def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def same_version(value, version):
    """With or without the epoch (2:4.0.4-9 or 4.0.4-9), alone or after the name (dpkg-query -W)."""
    value = (value.split() or [""])[-1]
    return value == version or value == version.split(":", 1)[-1]


# --- Debian -----------------------------------------------------------------------

def dpkg_installed(name):
    out = sh("dpkg-query", "-W", "-f", "${Status}\t${Version}", name)
    status, _, version = out.partition("\t")
    return version if status == "install ok installed" else None


def installed_setup(work, rng):
    found = [(p, v) for p in COMMON if (v := dpkg_installed(p))]
    name, version = rng.choice(found or [("dpkg", dpkg_installed("dpkg") or "")])
    return {"answer": version, "args": {"pkg": name}}


def candidate(name):
    for line in sh("apt-cache", "policy", name).splitlines():
        if line.strip().startswith("Candidate:"):
            value = line.split(":", 1)[1].strip()
            return None if value == "(none)" else value
    return None


def candidate_setup(work, rng):
    pool = [p for p in rng.sample(EXTRAS, len(EXTRAS)) if not dpkg_installed(p)]
    for name in pool:
        version = candidate(name)
        if version:
            break
    else:                                    # no package lists here: an installed package still has one
        name = rng.choice([p for p in COMMON if dpkg_installed(p)] or ["dpkg"])
        version = candidate(name) or dpkg_installed(name) or ""
    return {"answer": version, "args": {"pkg": name}}


def owned_files(listing, owner_of):
    """Programs in /usr/bin or /usr/sbin that `owner_of` gives back to exactly one package."""
    files = [f for f in listing if f.startswith(("/usr/bin/", "/usr/sbin/"))
             and os.path.isfile(f) and not os.path.islink(f)]
    return [(f, pkg) for f in files if (pkg := owner_of(f))]


def dpkg_owner(path):
    lines = [x for x in sh("dpkg", "-S", path).splitlines() if x.endswith(": " + path)]
    return lines[0].split(":")[0] if len(lines) == 1 and "," not in lines[0].split(": ")[0] else None


def owner_setup(work, rng, listing=lambda p: sh("dpkg", "-L", p).splitlines(), owner_of=dpkg_owner,
                installed=dpkg_installed):
    for name in rng.sample(COMMON, len(COMMON)):
        if installed(name):
            found = owned_files(listing(name), owner_of)
            if found:
                path, pkg = rng.choice(found)
                return {"answer": pkg, "args": {"path": path}}
    return {"answer": "coreutils", "args": {"path": "/usr/bin/ls"}}


def mark_setup(work, rng):
    manual = sh("apt-mark", "showmanual").split()
    auto = sh("apt-mark", "showauto").split()
    kind = rng.choice([k for k, pool in (("manual", manual), ("auto", auto)) if pool] or ["manual"])
    pool = manual if kind == "manual" else auto
    return {"answer": kind, "args": {"pkg": rng.choice(pool or ["dpkg"])}}


def mark_verify(work, meta, value):
    return value.strip().lower() == meta["answer"]


def version_verify(work, meta, value):
    return same_version(value, meta["answer"])


# --- Red Hat ------------------------------------------------------------------------

def rpm_version(name):
    """version-release, or None if not installed or installed twice (two architectures)."""
    out = sh("rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}\\n", name).splitlines()
    return out[0] if len(out) == 1 and "not installed" not in out[0] else None


def rpm_installed_setup(work, rng):
    found = [(p, v) for p in COMMON if (v := rpm_version(p))]
    name, version = rng.choice(found or [("rpm", rpm_version("rpm") or "")])
    return {"answer": version, "args": {"pkg": name}, "full": sh("rpm", "-q", name).strip()}


def rpm_version_verify(work, meta, value):
    return same_version(value, meta["answer"]) or value.strip() == meta.get("full")


def rpm_owner(path):
    out = sh("rpm", "-qf", "--qf", "%{NAME}\\n", path).splitlines()
    return out[0] if len(out) == 1 and " " not in out[0] else None


def rpm_owner_setup(work, rng):
    return owner_setup(work, rng, listing=lambda p: sh("rpm", "-ql", p).splitlines(), owner_of=rpm_owner,
                       installed=rpm_version)


def rpm_owner_verify(work, meta, value):
    """The name, or the full name-version-release.arch that `rpm -qf` prints."""
    value, name = value.strip(), meta["answer"]
    return value == name or value.startswith(name + "-") and value[len(name) + 1:][:1].isdigit()


def rpm_count_setup(work, rng):
    return {"answer": len(sh("rpm", "-qa").split())}


# --- the fights -------------------------------------------------------------------------

APT = ("apt", "dpkg", "dpkg-query", "apt-cache")
RPM = ("rpm", "dnf", "yum")

ALL = [
    Challenge(level=1, id="version_vole", pet="ant", tools=APT, distro=DEBIAN, skill="debian", requires=["dpkg-query"],
              threat="Version Vole",
              task="The Version Vole nibbles at labels. Which version of {pkg} is installed on this machine?\n"
                   "Ask the package database, then: answer <version>",
              hints=["apt list --installed shows what is on the machine, with versions; add a name to "
                     "see only that one. dpkg -l does it too.",
                     "Try: apt list --installed {pkg}   (or: dpkg-query -W {pkg})"],
              setup=installed_setup, verify=version_verify),
    Challenge(level=1, id="candidate_crow", pet="ant", tools=APT, distro=DEBIAN, skill="debian", requires=["apt-cache"],
              threat="Candidate Crow",
              task="The Candidate Crow wants what isn't here yet. Which version of {pkg} would apt install?\n"
                   "Don't install it: just ask apt, then: answer <version>",
              hints=["apt search name lists matching packages with the version apt would install; "
                     "apt policy name shows Installed and Candidate.",
                     "Try: apt policy {pkg}   (the Candidate: line)"],
              setup=candidate_setup, verify=version_verify),
    Challenge(level=2, id="stowaway_stoat", pet="ant", tools=APT, distro=DEBIAN, skill="debian", requires=["dpkg"],
              threat="Stowaway Stoat",
              task="The Stowaway Stoat asks: which package put {path} on this machine?\n"
                   "A file nobody owns in /usr/bin would be suspicious. Answer with the package name.",
              hints=["dpkg knows which package installed each file: dpkg -S path searches it.",
                     "Try: dpkg -S {path}"],
              setup=owner_setup),
    Challenge(level=2, id="autoremove_adder", pet="ant", tools=APT + ("apt-mark",), distro=DEBIAN, skill="debian",
              requires=["apt-mark"], threat="Autoremove Adder",
              task="The Autoremove Adder eats packages nobody asked for. Is {pkg} marked manual or auto?\n"
                   "(auto = pulled in as a dependency: apt autoremove may take it.) answer manual, or answer auto",
              hints=["apt-mark keeps the list: showmanual for what you asked for, showauto for dependencies.",
                     "Try: apt-mark showmanual | grep -x {pkg}   (nothing printed: it's auto)"],
              setup=mark_setup, verify=mark_verify),
    Challenge(level=1, id="release_raven", pet="ant", tools=RPM, distro=REDHAT, skill="rocky", requires=["rpm"],
              threat="Release Raven",
              task="The Release Raven collects version tags. Which version of {pkg} is installed here?\n"
                   "Answer version-release, like 5.1.8-9.el9: answer <version>",
              hints=["rpm -q name prints name-version-release.arch; dnf list --installed name shows it too.",
                     "Try: rpm -q {pkg}"],
              setup=rpm_installed_setup, verify=rpm_version_verify),
    Challenge(level=2, id="hitchhiker_hare", pet="ant", tools=RPM, distro=REDHAT, skill="rocky", requires=["rpm"],
              threat="Hitchhiker Hare",
              task="The Hitchhiker Hare asks: which package put {path} on this machine?\n"
                   "A file nobody owns in /usr/bin would be suspicious. Answer with the package name.",
              hints=["rpm knows which package installed each file: rpm -qf path.",
                     "Try: rpm -qf --qf '%{NAME}\\n' {path}"],
              setup=rpm_owner_setup, verify=rpm_owner_verify),
    Challenge(level=2, id="census_centipede", pet="ant", tools=RPM, distro=REDHAT, skill="rocky", requires=["rpm", "wc"],
              threat="Census Centipede",
              task="The Census Centipede counts legs, you count packages.\n"
                   "How many packages are installed on this machine?",
              hints=["rpm -qa lists every installed package, one per line. Something counts lines…",
                     "Try: rpm -qa | wc -l"],
              setup=rpm_count_setup),
]
