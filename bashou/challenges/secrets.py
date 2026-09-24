"""Secrets fights (owner, 2026-09-24): gpg and pass, "important for scripting safely". Lock a file with a
passphrase, open one, tell a genuine download from a forged one, read a password from a store, and take
a password out of a script.

Bashou never touches your own keys or your own store. Its gpg calls use a throwaway --homedir, killed
and removed right after. The pass fights bring their own practice key and store (gnupg/ and store/ in the
arena): the arena shell points GNUPGHOME and PASSWORD_STORE_DIR at them, and only there.
"""

import contextlib
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import Challenge

WORDS = ["amber", "birch", "comet", "delta", "ember", "fjord", "glade", "harbor", "iris", "juniper", "kelp",
         "lantern", "maple", "nectar", "orbit", "pepper", "quartz", "raven", "saffron", "tundra"]
PRACTICE_UID = "Bashou practice key <practice@bashou.invalid>"


def gpg(home, *args, input=None):
    """gpg on a homedir of ours, never asking anything (no pinentry: the passphrase comes as an argument)."""
    return subprocess.run(["gpg", "--homedir", str(home), "--batch", "--yes", "--quiet", "--pinentry-mode",
                           "loopback", *args], input=input, capture_output=True, timeout=60)


def stop_agent(home):
    """gpg starts an agent for each homedir: stop ours when we're done with it."""
    try:
        subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "all"], capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


@contextlib.contextmanager
def scratch_home():
    home = Path(tempfile.mkdtemp(prefix="bashou-gpg-"))                  # 0700, like ~/.gnupg
    try:
        yield home
    finally:
        stop_agent(home)
        shutil.rmtree(home, ignore_errors=True)


def passphrase(rng):
    return f"{rng.choice(WORDS)}-{rng.choice(WORDS)}-{rng.randint(10, 99)}"


def lock(src, out, pw):
    """Encrypt `src` with a passphrase into `out` (like gpg -c)."""
    with scratch_home() as home:
        gpg(home, "--passphrase", pw, "--no-symkey-cache", "--symmetric", "--output", str(out), str(src))


def unlock(path, pw):
    """The content of a gpg -c file, or None if the passphrase doesn't open it."""
    with scratch_home() as home:
        done = gpg(home, "--passphrase", pw, "--no-symkey-cache", "--decrypt", str(path))
    return done.stdout.decode(errors="replace") if done.returncode == 0 else None


def new_key(home, uid=PRACTICE_UID):
    """A key pair with no passphrase (signing + encryption subkey); its fingerprint."""
    gpg(home, "--passphrase", "", "--quick-generate-key", uid, "future-default", "default", "never")
    out = gpg(home, "--with-colons", "--list-secret-keys").stdout.decode()
    return next(line.split(":")[9] for line in out.splitlines() if line.startswith("fpr:"))


# --- lock a file: gpg -c ----------------------------------------------------------------------------

def seal_setup(work, rng):
    secret = f"wifi: {rng.choice(WORDS)}{rng.randint(1000, 9999)}\nbank pin: {rng.randint(1000, 9999)}\n"
    (work / "secrets.txt").write_text(secret)
    return {"args": {"pw": passphrase(rng)}, "secret": secret}


def seal_verify(work, meta, value):
    if (work / "secrets.txt").exists():
        return False                                        # the clear copy is still there
    locked = [p for p in (work / "secrets.txt.gpg", work / "secrets.txt.asc") if p.is_file()]
    return any(unlock(p, meta["args"]["pw"]) == meta["secret"] for p in locked)


# --- open a file: gpg -d ----------------------------------------------------------------------------

def message_setup(work, rng, name="message.txt"):
    code = f"{rng.choice(WORDS)}-{rng.randint(100, 999)}"
    pw = passphrase(rng)
    (work / name).write_text(f"Meet at the old bridge. The vault code is {code}.\n")
    lock(work / name, work / f"{name}.gpg", pw)
    (work / name).unlink()
    return {"args": {"pw": pw}, "answer": code}


# --- a genuine download: gpgv ------------------------------------------------------------------------

RELEASE = "tool-1.4.tar.gz"


def forged_setup(work, rng):
    with scratch_home() as home:
        new_key(home, "Bashou Tools releases <release@bashou.invalid>")
        (work / "vendor.gpg").write_bytes(gpg(home, "--export").stdout)
        for mirror in ("mirror1", "mirror2"):
            (work / mirror).mkdir()
            data = bytes(rng.getrandbits(8) for _ in range(2048))
            (work / mirror / RELEASE).write_bytes(data)
            gpg(home, "--passphrase", "", "--detach-sign", "--output", str(work / mirror / f"{RELEASE}.sig"),
                str(work / mirror / RELEASE))
    good = rng.choice(["mirror1", "mirror2"])
    bad = "mirror2" if good == "mirror1" else "mirror1"
    with open(work / bad / RELEASE, "ab") as f:
        f.write(b"\n# a little something extra\n")          # changed after it was signed
    return {"args": {}, "answer": good}


# --- a practice password store -------------------------------------------------------------------------

def practice_store(work, rng, entries):
    """gnupg/ (a practice key, no passphrase) and store/ (entries encrypted for it), as pass lays them out."""
    home, store = work / "gnupg", work / "store"
    home.mkdir(mode=0o700)
    store.mkdir()
    fpr = new_key(home)
    (store / ".gpg-id").write_text(fpr + "\n")
    for name, secret in entries.items():
        path = store / f"{name}.gpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        gpg(home, "--trust-model", "always", "--encrypt", "--recipient", fpr, "--output", str(path),
            input=(secret + "\n").encode())
    return {"GNUPGHOME": str(home), "PASSWORD_STORE_DIR": str(store)}


def practice_cleanup(meta):
    if meta.get("env", {}).get("GNUPGHOME"):
        stop_agent(meta["env"]["GNUPGHOME"])


def random_password(rng, n=16):
    return "".join(rng.choice("abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(n))


def vault_setup(work, rng):
    entries = {name: random_password(rng) for name in ("backup/server", "web/forum", "mail/work", "wifi/home")}
    return {"args": {}, "answer": entries["backup/server"], "env": practice_store(work, rng, entries)}


DEPLOY = """#!/usr/bin/env bash
# deploy.sh: logs in to the database, then deploys the app.
set -euo pipefail

DB_PASSWORD="{pw}"

if [ "$(printf %s "$DB_PASSWORD" | sha256sum | cut -d' ' -f1)" = "{hash}" ]; then
  echo "login ok: deploying"
else
  echo "login failed" >&2
  exit 1
fi
"""


def cleartext_setup(work, rng):
    pw = random_password(rng, 20)
    env = practice_store(work, rng, {"db/prod": pw, "web/admin": random_password(rng)})
    digest = hashlib.sha256(pw.encode()).hexdigest()
    (work / "deploy.sh").write_text(DEPLOY.format(pw=pw, hash=digest))
    return {"args": {}, "pw": pw, "hash": digest, "env": env}


def cleartext_verify(work, meta, value):
    """The password is gone from the script, and the script still logs in (reading it from the store)."""
    try:
        text = (work / "deploy.sh").read_text()
    except OSError:
        return False
    if meta["pw"] in text or meta["hash"] not in text:
        return False
    try:
        run = subprocess.run(["bash", str(work / "deploy.sh")], cwd=work, capture_output=True, text=True, timeout=30,
                             env={**os.environ, **meta["env"]}, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "login ok" in run.stdout


# --- the fights -----------------------------------------------------------------------------------

PINENTRY = ("If gpg says it can't ask for the passphrase, add --pinentry-mode loopback and it asks right "
            "here in the terminal.")
GPG = dict(pet="leopard", tools=("gpg", "gpg2"), requires=["gpg", "gpgconf"], skill="linux")
PASS = dict(pet="leopard", tools=("pass",), requires=["pass", "gpg", "gpgconf"], skill="linux", cleanup=practice_cleanup)

ALL = [
    Challenge(level=1, id="plaintext_pixie", threat="Plaintext Pixie", **GPG, fix=True,
              task="The Plaintext Pixie left secrets.txt in clear: anyone who gets the disk or a backup can read it.\n"
                   "Lock it with gpg and the passphrase {pw}, then delete the clear file, so only secrets.txt.gpg is "
                   "left. (In real life, choose your own passphrase and never write it down.) Then: verify",
              hints=["gpg -c (symmetric) locks a file with a passphrase: the same passphrase opens it. It writes "
                     "secrets.txt.gpg next to the file and keeps the original, so you remove that one yourself.",
                     "gpg -c secrets.txt, type {pw} twice, then rm secrets.txt. " + PINENTRY],
              help="Look for the option that encrypts with a passphrase only (symmetric).",
              setup=seal_setup, verify=seal_verify),
    Challenge(level=1, id="cipher_crow", threat="Cipher Crow", **GPG,
              task="The Cipher Crow dropped message.txt.gpg, locked with the passphrase {pw}.\n"
                   "Open it: what is the vault code? answer <code>",
              hints=["gpg -d (decrypt) opens a locked file: it asks for the passphrase, then prints the content. "
                     "-o file writes it to a file instead of the screen.",
                     "gpg -d message.txt.gpg, then type {pw}. " + PINENTRY],
              help="Look for the option that decrypts.",
              setup=message_setup),
    Challenge(level=2, id="forger_ferret", threat="Forger Ferret", pet="leopard", tools=("gpgv", "gpg", "gpg2"),
              requires=["gpgv", "gpg", "gpgconf"], skill="linux", after=("cipher_crow",),
              task="The Forger Ferret put the same release, " + RELEASE + ", on two mirrors: mirror1/ and mirror2/, "
                   "each with its signature (.sig). The vendor's public key is vendor.gpg.\nOnly one download is "
                   "genuine. Which mirror? answer <mirror1|mirror2>",
              hints=["A signature proves who made a file, and that nothing changed since. gpgv checks it against a "
                     "keyring you choose, without adding anything to your own keys: gpgv --keyring ./vendor.gpg "
                     "file.sig file (the ./ matters: without it, gpgv looks in ~/.gnupg).",
                     "gpgv --keyring ./vendor.gpg mirror1/" + RELEASE + ".sig mirror1/" + RELEASE + ", then the same "
                     "for mirror2. \"Good signature\" means genuine; \"BAD signature\" means changed after signing."],
              setup=forged_setup),
    Challenge(level=1, id="vault_vole", threat="Vault Vole", **PASS,
              task="The Vault Vole guards a practice password store. In this arena, pass and gpg use it and its own "
                   "practice key (store/ and gnupg/): your own keys and passwords are not touched.\nWhat is the "
                   "password of backup/server? answer <password>",
              hints=["pass keeps each password in its own file, encrypted with gpg: backup/server is "
                     "store/backup/server.gpg. pass ls lists the names; pass show <name> prints one.",
                     "pass show backup/server"],
              setup=vault_setup),
    Challenge(level=2, id="cleartext_cricket", threat="Cleartext Cricket", **PASS, fix=True, after=("vault_vole",),
              task="The Cleartext Cricket wrote the database password in clear in deploy.sh: whoever reads the "
                   "script, or its git history, gets it. The password is already in the store as db/prod.\nMake the "
                   "script read it with pass, so it's no longer written in the file, and still logs in "
                   "(bash deploy.sh). Then: verify",
              hints=["$( ) runs a command and puts what it prints in its place. pass show db/prod prints the "
                     "password, so the variable is filled when the script runs, and the file never holds it.",
                     "Change the line to DB_PASSWORD=\"$(pass show db/prod)\" and try bash deploy.sh. In real "
                     "life, also change a password that was ever committed: it stays in the git history."],
              setup=cleartext_setup, verify=cleartext_verify),
]

# The Sage Owl's chest for gpg.
from .trials import trial  # noqa: E402

CHEST = trial("trial_gpg_note", 1, "A locked note lies in this chest: note.txt.gpg, passphrase {pw}. Open it: "
              "what is the vault code? answer <code>",
              ["gpg -d opens a file locked with gpg -c: it asks for the passphrase and prints the content.",
               "gpg -d note.txt.gpg, then type {pw}. " + PINENTRY],
              lambda work, rng: message_setup(work, rng, "note.txt"), lambda w, m, v: v.strip() == m["answer"],
              requires=["gpg", "gpgconf"], teaches=["gpg"])
