"""Repository fights (owner, 2026-09-23): fix a broken apt or dnf repository file (look the right values
up online, or in your own /etc), and restrict one dnf command to a single repository.

The files live in the arena: nothing on the system changes. They are checked by meaning, not letter by
letter: http or https, a trailing slash, extra components or backports are all fine.
"""

import configparser
import shlex
import shutil
from pathlib import Path

from . import Challenge
from ..analyze import parse_log

# The first one installed is the one the threat names (a minimal Rocky has vi, not nano).
EDITORS = tuple(sorted(("nano", "vim", "vi", "nvim", "emacs", "micro", "sed"), key=lambda e: not shutil.which(e)))
KEYRINGS = {"/usr/share/keyrings/debian-archive-keyring.gpg", "/usr/share/keyrings/debian-archive-keyring.pgp"}
REPOS = Path("/etc/yum.repos.d")

DEBIAN_OK = """Types: deb
URIs: https://deb.debian.org/debian
Suites: trixie trixie-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp

Types: deb
URIs: https://security.debian.org/debian-security
Suites: trixie-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp
"""

# (what the right file says, a plausible mistake), each applied once
DEBIAN_MISTAKES = [
    ("URIs: https://deb.debian.org/debian\n", "URIs: https://deb.debain.org/debian\n"),
    ("URIs: https://deb.debian.org/debian\n", "URIs: https://deb.debian.org/debain\n"),
    ("Suites: trixie trixie-updates", "Suites: trixy trixie-updates"),
    ("Suites: trixie trixie-updates", "Suites: trixie trixie-update"),
    ("Suites: trixie-security", "Suites: trixie/updates"),
    ("URIs: https://security.debian.org/debian-security", "URIs: https://security.debian.org/debian"),
    ("Components: main\nSigned", "Components: mian\nSigned"),
    ("Types: deb\nURIs: https://security", "Types: debs\nURIs: https://security"),
    ("debian-archive-keyring.pgp\n\n", "debian-archive-keyring.asc\n\n"),
]


def plant(text, mistakes, rng, n=3):
    """Apply n mistakes that don't touch the same line."""
    done, lines = 0, set()
    for right, wrong in rng.sample(mistakes, len(mistakes)):
        if done == n:
            break
        at = text.find(right)
        line = text.count("\n", 0, at)
        if at < 0 or line in lines:
            continue
        text = text[:at] + wrong + text[at + len(right):]
        lines.add(line)
        done += 1
    return text


def stanzas(text):
    found = []
    for block in text.strip().split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, sep, value = line.partition(":")
            if sep and not line.startswith("#"):
                fields[key.strip().lower()] = value.strip()
        if fields:
            found.append(fields)
    return found


def uri(value):
    return value.rstrip("/").replace("http://", "https://")


def debian_verify(work, meta, value):
    try:
        found = stanzas((work / "debian.sources").read_text())
    except OSError:
        return False
    if len(found) != 2 or any(s.get("types") != "deb" or s.get("signed-by") not in KEYRINGS for s in found):
        return False
    main = next((s for s in found if uri(s.get("uris", "")) == "https://deb.debian.org/debian"), None)
    sec = next((s for s in found if uri(s.get("uris", "")) == "https://security.debian.org/debian-security"), None)
    if not main or not sec:
        return False
    components_ok = all({"main"} <= set(s.get("components", "").split())
                        <= {"main", "contrib", "non-free", "non-free-firmware"} for s in found)
    return (components_ok and {"trixie", "trixie-updates"} <= set(main.get("suites", "").split())
            <= {"trixie", "trixie-updates", "trixie-backports"} and sec.get("suites") == "trixie-security")


def debian_setup(work, rng):
    (work / "debian.sources").write_text(plant(DEBIAN_OK, DEBIAN_MISTAKES, rng))
    return {}


ROCKY_OK = """[baseos]
name=Rocky Linux $releasever - BaseOS
baseurl=https://dl.rockylinux.org/pub/rocky/$releasever/BaseOS/$basearch/os/
gpgcheck=1
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9

[appstream]
name=Rocky Linux $releasever - AppStream
baseurl=https://dl.rockylinux.org/pub/rocky/$releasever/AppStream/$basearch/os/
gpgcheck=1
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9
"""

ROCKY_MISTAKES = [
    ("/BaseOS/", "/BaseOs/"),
    ("/AppStream/", "/Appstream/"),
    ("https://dl.rockylinux.org/pub/rocky/$releasever/BaseOS", "https://dl.rockylinux.com/pub/rocky/$releasever/BaseOS"),
    ("AppStream/$basearch", "AppStream/$basearh"),
    ("gpgcheck=1\nenabled=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9\n\n",
     "gpgcheck=0\nenabled=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9\n\n"),
    ("RPM-GPG-KEY-Rocky-9\n\n[appstream]", "RPM-GPG-KEY-rocky-9\n\n[appstream]"),
    ("os/\ngpgcheck=1\nenabled=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9\n",
     "os/\ngpgcheck=1\nenabled=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-8\n"),
    ("BaseOS/$basearch/os/\ngpgcheck=1\nenabled=1", "BaseOS/$basearch/os/\ngpgcheck=1\nenabled=0"),
]

MIRRORLIST = "https://mirrors.rockylinux.org/mirrorlist?arch=$basearch&repo={repo}-$releasever"


def rocky_verify(work, meta, value):
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string((work / "rocky.repo").read_text())
    except (OSError, configparser.Error):
        return False
    for section, repo in (("baseos", "BaseOS"), ("appstream", "AppStream")):
        if section not in parser:
            return False
        r = parser[section]
        base = uri(r.get("baseurl", "")) == f"https://dl.rockylinux.org/pub/rocky/$releasever/{repo}/$basearch/os"
        mirror = r.get("mirrorlist", "").split("$rltype")[0] == MIRRORLIST.format(repo=repo)
        if not (base or mirror) or r.get("gpgcheck") != "1" or r.get("enabled", "1") != "1":
            return False
        if r.get("gpgkey") != "file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9":
            return False
    return True


def rocky_setup(work, rng):
    (work / "rocky.repo").write_text(plant(ROCKY_OK, ROCKY_MISTAKES, rng))
    return {}


# --- one command, one repository --------------------------------------------------------

def enabled_repos(folder=None):
    """Repository ids enabled in /etc/yum.repos.d (enabled= missing means enabled)."""
    found = []
    for path in sorted(Path(folder or REPOS).glob("*.repo")):
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read_string(path.read_text())
        except (OSError, configparser.Error):
            continue
        found += [s for s in parser.sections() if parser[s].get("enabled", "1").strip() == "1"]
    return found


def only_repo(words):
    """The single repository a dnf command line is limited to, or None."""
    enabled, disabled_all, i = [], False, 0
    while i < len(words):
        word = words[i]
        name, sep, value = word.partition("=")
        if name in ("--disablerepo", "--enablerepo", "--repo", "--repoid") and not sep and i + 1 < len(words):
            value, i = words[i + 1], i + 1
        if name == "--disablerepo" and value == "*":
            disabled_all = True
        elif name == "--enablerepo" and disabled_all or name in ("--repo", "--repoid"):
            enabled += value.split(",")
        i += 1
    return enabled[0] if len(enabled) == 1 else None


def restricted(analysis):
    return any(name in ("dnf", "yum") and only_repo(args) for name, args in analysis.commands)


def enabled_setup(work, rng):
    repos = enabled_repos()
    return {"args": {"repo": rng.choice(repos) if repos else "baseos"}}


def enabled_verify(work, meta, value):
    """A successful dnf/yum command in this arena, limited to the asked repository."""
    try:
        records = parse_log((Path(work).parent / "log").read_text())
    except OSError:
        return False
    for status, command in records:
        try:
            words = shlex.split(command)
        except ValueError:
            continue
        if status == 0 and words[:1] and words[0] in ("dnf", "yum", "sudo") and \
                only_repo(words) == meta["args"]["repo"]:
            return True
    return False


DEBIAN = ("debian",)
REDHAT = ("rhel", "fedora", "centos")

ALL = [
    Challenge(level=2, id="mirror_mimic", pet="ant", tools=EDITORS, distro=DEBIAN, skill="debian", requires=["sed"],
              threat="Mirror Mimic",
              task="The Mirror Mimic copied debian.sources and slipped in 3 mistakes.\n"
                   "Fix it for Debian 13 trixie: main archive with trixie-updates, plus security. Look up the "
                   "right values online, or in your own /etc/apt/sources.list.d. Then: answer done",
              hints=["Official lines: wiki.debian.org/SourcesList. `man sources.list` explains each field. "
                     "Since Debian 11, security uses <release>-security.",
                     "Compare: diff debian.sources /etc/apt/sources.list.d/debian.sources (if you run trixie)."],
              setup=debian_setup, verify=debian_verify),
    Challenge(level=2, id="repo_revenant", pet="ant", tools=EDITORS, distro=REDHAT, skill="rocky", requires=["sed"],
              threat="Repo Revenant",
              task="The Repo Revenant haunts rocky.repo: 3 mistakes in the BaseOS and AppStream repos.\n"
                   "Fix it for Rocky Linux 9 (browse dl.rockylinux.org/pub/rocky/9/ to check paths). "
                   "Then: answer done",
              hints=["Paths are case-sensitive: open dl.rockylinux.org/pub/rocky/9/ in a browser and follow them. "
                     "gpgcheck must stay 1, and the key must be Rocky 9's.",
                     "Compare with /etc/yum.repos.d/rocky.repo on a Rocky 9 machine: "
                     "baseurl=https://dl.rockylinux.org/pub/rocky/$releasever/BaseOS/$basearch/os/"],
              setup=rocky_setup, verify=rocky_verify),
    Challenge(level=2, id="enabled_ettin", pet="ant", tools=("dnf", "yum"), distro=REDHAT, skill="rocky", requires=["dnf"],
              uses=restricted, threat="Enabled Ettin",
              task="The Enabled Ettin has one head per repository. Cut all but one, for one command:\n"
                   "run a dnf command (search, list, repolist…) that uses only the {repo} repository, "
                   "without editing any file. Then: answer done",
              hints=["dnf takes --disablerepo and --enablerepo on the command line: disable them all, "
                     "then enable the one you need. Quote the * so bash leaves it alone.",
                     "Try: dnf --disablerepo='*' --enablerepo={repo} repolist   (or: dnf --repo={repo} repolist)"],
              setup=enabled_setup, verify=enabled_verify),
]
