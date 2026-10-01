"""Linux fights: who you are, file rights, what fills the disk, archives, a service's unit file, and
the headers a web server sends."""

import configparser
import grp
import io
import os
import tarfile

from . import Challenge
from .network import loopback_works, serve, stop
from .repos import EDITORS
from .trials import trial

ROOMS = ("attic", "cellar", "garage", "kitchen", "library", "loft", "porch", "shed", "studio", "vault")


# --- Group Gremlin: id -------------------------------------------------------------------------------

def main_group():
    try:
        return grp.getgrgid(os.getgid()).gr_name
    except KeyError:
        return str(os.getgid())


GROUP_GREMLIN = Challenge(
    level=1, id="group_gremlin", pet="hedgehog", tools=("id", "groups"), threat="Group Gremlin", requires=["id"],
    skill="linux",
    task="The Group Gremlin wants to know which team you play for.\nWhat is the name of your main group (your "
         "primary group)?",
    help="Here, find the option that prints only the group, and the one that prints names instead of numbers.",
    hints=["Every user has a number (uid) and belongs to groups: one main group, which new files get, and maybe "
           "others. id prints all of it at once: uid, gid (the main group) and groups. The name is in "
           "brackets after gid=.",
           "Try: id (look at gid=...) or id -gn, which prints just the main group's name."],
    setup=lambda work, rng: {},
    verify=lambda w, m, v: v.strip() in {main_group(), str(os.getgid())},
)


# --- Chmod Chimera: the right rights on two files -----------------------------------------------------

def rights_setup(work, rng):
    (work / "diary.txt").write_text("Dear diary, today I learned chmod.\n")
    (work / "diary.txt").chmod(0o666)
    (work / "backup.sh").write_text("#!/bin/bash\necho backing up\n")
    (work / "backup.sh").chmod(0o600)
    return {}


def rights_verify(work, meta, value):
    def mode(name):
        path = work / name
        return path.stat().st_mode & 0o777 if path.is_file() else None
    return mode("diary.txt") == 0o600 and mode("backup.sh") == 0o755


CHMOD_CHIMERA = Challenge(
    level=1, id="chmod_chimera", pet="hedgehog", tools=("chmod",), threat="Chmod Chimera", requires=["chmod"],
    skill="linux", fix=True,
    task="The Chmod Chimera mixed up the rights.\ndiary.txt: only you may read and write it, nobody else gets "
         "anything (rw-------). backup.sh: you may do everything, everyone else may read and run it "
         "(rwxr-xr-x). Then: verify",
    help="Here, look at how MODE is written: u, g, o (user, group, others) with +, - or =, or a number.",
    hints=["ls -l shows the rights in three groups of three letters: you (user), your group, everyone else "
           "(others). r = read, w = write, x = run. In numbers, r = 4, w = 2, x = 1, added up per group: "
           "rw- = 6, r-x = 5, rwx = 7, --- = 0.",
           "Try: chmod 600 diary.txt and chmod 755 backup.sh, then ls -l to check."],
    setup=rights_setup, verify=rights_verify,
)


# --- Hoarder Hog: du, and which folder is the biggest ------------------------------------------------

def hoard_setup(work, rng):
    big, many, small = rng.sample(ROOMS, 3)
    (work / big).mkdir()
    (work / big / "video.bin").write_bytes(b"v" * rng.randint(3_000_000, 4_000_000))
    (work / many).mkdir()
    for i in range(40):                                   # the most files, not the most space
        (work / many / f"note{i:02}.txt").write_bytes(b"n" * rng.randint(10_000, 20_000))
    (work / small).mkdir()
    for i in range(3):
        (work / small / f"photo{i}.jpg").write_bytes(b"p" * rng.randint(100_000, 200_000))
    return {"answer": big}


HOARDER_HOG = Challenge(
    level=1, id="hoarder_hog", pet="meerkat", tools=("du",), threat="Hoarder Hog", requires=["du"], skill="linux",
    task="The Hoarder Hog stuffed three folders here. Which folder takes the most disk space?",
    help="Here, find -s (one total per folder) and -h (sizes people can read: K, M, G).",
    hints=["ls shows files, not how much space a folder uses with everything inside. du (disk usage) adds it "
           "up. Careful: the folder with the most files isn't always the biggest.",
           "Try: du -sh * (sort -h puts the biggest last: du -sh * | sort -h)"],
    setup=hoard_setup, verify=lambda w, m, v: v.strip().rstrip("/") == m["answer"],
)


# --- Tar Tortoise: unpack an archive into a folder ---------------------------------------------------

def archive_setup(work, rng):
    files = {"project/notes.txt": f"meeting in the {rng.choice(ROOMS)}\n",
             "project/todo.txt": "water the plants\n",
             f"project/data/{rng.choice(ROOMS)}.csv": "item,count\nchairs,4\n"}
    with tarfile.open(work / "backup.tar.gz", "w:gz") as tar:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
    (work / "restore").mkdir()
    return {"files": files}


def archive_verify(work, meta, value):
    return all((work / "restore" / name).is_file() and (work / "restore" / name).read_text() == text
               for name, text in meta["files"].items())


TAR_TORTOISE = Challenge(
    level=1, id="tar_tortoise", pet="squirrel", tools=("tar",), threat="Tar Tortoise", requires=["tar", "gzip"],
    skill="linux", fix=True,
    task="The Tar Tortoise sat on backup.tar.gz. Unpack it into the folder restore/ (it's already there), "
         "keeping its folders. Then: verify",
    help="Here, find -x (extract), -z (gzip), -f (the archive's file) and -C (the folder to unpack into).",
    hints=["A .tar.gz is many files packed into one (tar), then squeezed (gzip). tar -tzf backup.tar.gz lists "
           "what's inside without unpacking. -x unpacks, and -C picks where: by default it's the folder "
           "you're in.",
           "Try: tar -xzf backup.tar.gz -C restore/, then ls -R restore"],
    setup=archive_setup, verify=archive_verify,
)


# --- Unit Imp: two lines in the wrong sections of a unit file ----------------------------------------

UNIT = """[Unit]
Description=The {name} bakery app
After=network.target

[Service]
WantedBy=multi-user.target
Restart=on-failure

[Install]
ExecStart=/usr/bin/python3 /opt/{name}/app.py
"""


def unit_setup(work, rng):
    name = rng.choice(("croissant", "baguette", "brioche", "eclair"))
    (work / f"{name}.service").write_text(UNIT.format(name=name))
    return {"args": {"unit": f"{name}.service"}, "name": name}


def unit_verify(work, meta, value):
    """ExecStart in [Service], WantedBy in [Install], and the rest as it was."""
    path = work / meta["args"]["unit"]
    if not path.is_file():
        return False
    unit = configparser.ConfigParser(strict=False, interpolation=None)
    unit.optionxform = str
    try:
        unit.read_string(path.read_text())
    except configparser.Error:
        return False
    sections = {s: dict(unit[s]) for s in unit.sections()}
    return (sections.get("Service", {}).get("ExecStart") == f"/usr/bin/python3 /opt/{meta['name']}/app.py"
            and sections.get("Service", {}).get("Restart") == "on-failure"
            and sections.get("Install") == {"WantedBy": "multi-user.target"}
            and sections.get("Unit", {}).get("After") == "network.target")


UNIT_IMP = Challenge(
    level=1, id="unit_imp", pet="bee", tools=EDITORS, threat="Unit Imp", requires=["sed"], skill="systemd", fix=True,
    task="The Unit Imp swapped two lines of {unit}: systemd would refuse to start it.\nPut each line back in "
         "its section. Then: verify",
    hints=["A unit file has sections in [brackets]. [Unit] describes it, [Service] says how to run it "
           "(ExecStart is the command), [Install] says when it starts with `systemctl enable` (WantedBy). "
           "Read it with cat {unit}: which line is in the wrong place?",
           "ExecStart=... belongs under [Service], WantedBy=multi-user.target under [Install]. Open {editor} "
           "{unit}, swap the two lines, {save_keys}."],
    setup=unit_setup, verify=unit_verify,
)


# --- Header Hound: curl -I --------------------------------------------------------------------------

def hound_setup(work, rng):
    port, pid = serve(work, rng)
    size = rng.randint(20_000, 90_000)
    (work.parent / "www" / "report.csv").write_bytes(b"x" * size)
    return {"args": {"port": port}, "answer": size, "pid": pid}


HEADER_HOUND = Challenge(
    level=1, id="header_hound", pet="pigeon", tools=("curl", "wget"), threat="Header Hound", requires=["curl"],
    skill="network", cleanup=stop, works=loopback_works,
    task="The Header Hound guards a web server on http://127.0.0.1:{port}.\nHow big is /report.csv, in bytes? "
         "Ask the server without downloading the file.",
    help="Here, find -I (--head): only the headers, not the file.",
    hints=["Before the file itself, a web server sends headers: a few lines about it, like Content-Type and "
           "Content-Length (its size in bytes). curl -I asks for the headers only.",
           "Try: curl -I http://127.0.0.1:{port}/report.csv and read the Content-Length line."],
    setup=hound_setup,
)

ALL = [GROUP_GREMLIN, CHMOD_CHIMERA, HOARDER_HOG, TAR_TORTOISE, UNIT_IMP, HEADER_HOUND]


# --- the chests after the road lessons "Rights, disk and archives" and "Services" ----------------------

def diary_setup(work, rng):
    (work / "diary.txt").write_text("my secrets\n")
    (work / "diary.txt").chmod(0o644)
    return {}


RIGHTS_CHEST = trial("trial_private_diary", 1, "A diary in this chest, diary.txt, can be read by everyone. Make "
                     "it yours only: read and write for you, nothing for the others. Then: verify",
                     ["ls -l diary.txt shows rw-r--r--: everyone may read it. 6 = rw for you, 0 for the group, "
                      "0 for others.", "Try: chmod 600 diary.txt"],
                     diary_setup, lambda w, m, v: (w / "diary.txt").stat().st_mode & 0o777 == 0o600,
                     requires=["chmod"], teaches=["chmod"])
UNIT_CHEST = trial("trial_unit_file", 1, "A broken unit file lies in this chest, {unit}. Put each line back "
                   "in its section. Then: verify", UNIT_IMP.hints, unit_setup, unit_verify, requires=["sed"],
                   teaches=["systemctl"])
CHESTS = [RIGHTS_CHEST, UNIT_CHEST]
