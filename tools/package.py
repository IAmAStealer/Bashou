"""Build Bashou's .deb and .rpm, and the signed apt + dnf repositories published on GitHub Pages.

    python3 tools/package.py build v0.4.1 dist/          # dist/bashou_0.4.1_all.deb, bashou-0.4.1-1.noarch.rpm
    python3 tools/package.py repo dist/ site/ KEYID      # site/deb, site/rpm, site/bashou.asc, signed with KEYID
    python3 tools/package.py site site/                  # only the share page, to try it: python3 -m http.server -d site

The code goes to /usr/share/bashou (the same tree as a clone, plus a VERSION file) and /usr/bin/bashou runs
its commands. Nothing turns the pet on: each user runs `bashou setup` once. `build` needs dpkg-deb for the
.deb and rpmbuild for the .rpm (either is skipped when missing); `repo` needs apt-ftparchive, createrepo_c,
rpmsign and gpg.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "usr/share/bashou"
SHIPPED = ("bashou/", "art/", "bashou.bash", "launch.py", "CHANGELOG.md", "LICENSE", "README.md")
URL = "https://github.com/IAmAStealer/Bashou"
PAGES = "https://iamastealer.github.io/Bashou"
SUMMARY = "A pet in your terminal that grows as you learn bash"
DESCRIPTION = ("Bashou lives in the corner of your terminal and evolves as you use bash: fights, a quiz\n"
               "adventure and hints teach the command line, offline. Each user turns it on with: bashou setup")

WRAPPER = f"""#!/bin/sh
# Bashou's commands outside the shell function it defines, e.g. `bashou setup` in a new account.
exec python3 /{PREFIX}/launch.py bashou "$@"
"""

# Users can't write to /usr/share: compile once at install so every command starts fast.
COMPILE = f"python3 -m compileall -q /{PREFIX}/bashou >/dev/null 2>&1 || true"
CLEAN = f"find /{PREFIX} -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null || true"

CONTROL = """Package: bashou
Version: {version}
Architecture: all
Maintainer: Bashou <noreply@github.com>
Depends: bash (>= 4.4), python3 (>= 3.9)
Section: games
Priority: optional
Homepage: {url}
Description: {summary}
{description}
"""

SPEC = """Name: bashou
Version: {version}
Release: 1
Summary: {summary}
License: MIT
URL: {url}
BuildArch: noarch
Requires: bash >= 4.4
Requires: python3 >= 3.9
# Plain files in /usr/share: no byte-compiling, no shebang rewriting, no automatic dependencies.
%global __brp_python_bytecompile %{{nil}}
%global __brp_mangle_shebangs %{{nil}}
AutoReqProv: no

%description
{description}

%install
cp -a {tree}/. %{{buildroot}}/

%post
{compile}

%preun
if [ "$1" -eq 0 ]; then {clean}; fi

%files
/{prefix}
/usr/bin/bashou
"""


DNF_REPO = f"""[bashou]
name=Bashou
baseurl={PAGES}/rpm/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey={PAGES}/bashou.asc
metadata_expire=6h
"""


def shipped_files():
    """Tracked files only: local notes and caches never end up in a package."""
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", *SHIPPED], capture_output=True, text=True,
                         check=True).stdout
    return [f for f in out.split("\0") if f and not f.endswith((".pyc", ".swp"))]


def stage(dest, version):
    """The installed tree: /usr/share/bashou (+ VERSION) and /usr/bin/bashou, with plain permissions."""
    share = dest / PREFIX
    for name in shipped_files():
        target = share / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (share / "VERSION").write_text(f"v{version}\n")
    (dest / "usr/bin").mkdir(parents=True)
    (dest / "usr/bin/bashou").write_text(WRAPPER)
    for path in [dest, *dest.rglob("*")]:
        path.chmod(0o755 if path.is_dir() or path.parent.name == "bin" else 0o644)
    return dest


def build_deb(tree, version, out):
    doc = tree / "usr/share/doc/bashou"
    doc.mkdir(parents=True, mode=0o755)
    shutil.copyfile(ROOT / "LICENSE", doc / "copyright")
    (doc / "copyright").chmod(0o644)
    (tree / "DEBIAN").mkdir(mode=0o755)
    description = "\n".join(" " + (line or ".") for line in DESCRIPTION.splitlines())
    (tree / "DEBIAN/control").write_text(CONTROL.format(version=version, url=URL, summary=SUMMARY,
                                                        description=description))
    for name, command in (("postinst", COMPILE), ("prerm", CLEAN)):
        (tree / "DEBIAN" / name).write_text(f"#!/bin/sh\nset -e\n{command}\n")
        (tree / "DEBIAN" / name).chmod(0o755)
    target = out / f"bashou_{version}_all.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(tree), str(target)], check=True,
                   stdout=subprocess.DEVNULL)
    shutil.rmtree(tree / "DEBIAN")
    shutil.rmtree(tree / "usr/share/doc")
    return target


def build_rpm(tree, version, out, work):
    spec = work / "bashou.spec"
    spec.write_text(SPEC.format(version=version, summary=SUMMARY, url=URL, description=DESCRIPTION,
                                tree=tree, prefix=PREFIX, compile=COMPILE, clean=CLEAN))
    subprocess.run(["rpmbuild", "-bb", "--quiet", "--define", f"_topdir {work / 'rpmbuild'}", str(spec)],
                   check=True)
    built = next((work / "rpmbuild/RPMS/noarch").glob("bashou-*.rpm"))
    return Path(shutil.copy(built, out))


def build(tag, out):
    version = tag.lstrip("v")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    made = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tree = stage(tmp / "tree", version)
        if shutil.which("dpkg-deb"):
            made.append(build_deb(tree, version, out))
        if shutil.which("rpmbuild"):
            made.append(build_rpm(tree, version, out, tmp))
    for path in made:
        print(path)
    return 0 if made else 1


def gpg(*args, **kw):
    return subprocess.run(["gpg", "--batch", "--yes", *args], check=True, **kw)


def apt_repo(debs, site, key):
    """A flat repository: Packages and a signed InRelease next to the .deb files (Suites: ./)."""
    folder = site / "deb"
    folder.mkdir(parents=True)
    for deb in debs:
        shutil.copy(deb, folder)
    with open(folder / "Packages", "w") as fh:
        subprocess.run(["apt-ftparchive", "packages", "."], cwd=folder, stdout=fh, check=True)
    subprocess.run(["gzip", "-k9", "Packages"], cwd=folder, check=True)
    with open(folder / "Release", "w") as fh:
        subprocess.run(["apt-ftparchive", "-o", "APT::FTPArchive::Release::Origin=Bashou",
                        "-o", "APT::FTPArchive::Release::Label=Bashou", "release", "."],
                       cwd=folder, stdout=fh, check=True)
    gpg("--local-user", key, "--clearsign", "-o", str(folder / "InRelease"), str(folder / "Release"))
    gpg("--local-user", key, "--armor", "--detach-sign", "-o", str(folder / "Release.gpg"), str(folder / "Release"))


def dnf_repo(rpms, site, key):
    """Signed packages, and signed metadata (repo_gpgcheck=1)."""
    folder = site / "rpm"
    folder.mkdir(parents=True)
    for rpm in rpms:
        target = Path(shutil.copy(rpm, folder))
        subprocess.run(["rpmsign", "--addsign", "--define", f"_gpg_name {key}",
                        "--define", f"__gpg {shutil.which('gpg')}", str(target)], check=True,
                       stdout=subprocess.DEVNULL)
    subprocess.run(["createrepo_c", "--quiet", str(folder)], check=True)
    repomd = folder / "repodata/repomd.xml"
    gpg("--local-user", key, "--armor", "--detach-sign", "-o", f"{repomd}.asc", str(repomd))


def site_pages(site):
    """The share page (doc/site) and the pets it may draw: `bashou share` links there."""
    sys.path.insert(0, str(ROOT))
    from bashou import share
    for page in sorted((ROOT / "doc/site").iterdir()):
        shutil.copyfile(page, site / page.name)
    (site / "share-pets.json").write_text(json.dumps(share.page_data(), separators=(",", ":")))


def repo(dist, site, key):
    dist, site = Path(dist), Path(site)
    site.mkdir(parents=True, exist_ok=True)
    with open(site / "bashou.asc", "wb") as fh:
        gpg("--armor", "--export", key, stdout=fh)
    apt_repo(sorted(dist.glob("*.deb")), site, key)
    dnf_repo(sorted(dist.glob("*.rpm")), site, key)
    (site / "bashou.repo").write_text(DNF_REPO)
    shutil.copyfile(ROOT / "doc/install.html", site / "index.html")
    site_pages(site)
    (site / ".nojekyll").touch()
    return 0


def main(argv):
    if len(argv) == 3 and argv[0] == "build":
        return build(argv[1], argv[2])
    if len(argv) == 2 and argv[0] == "site":
        Path(argv[1]).mkdir(parents=True, exist_ok=True)
        site_pages(Path(argv[1]))
        return 0
    if len(argv) == 4 and argv[0] == "repo":
        return repo(*argv[1:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    os.umask(0o022)
    sys.exit(main(sys.argv[1:]))
