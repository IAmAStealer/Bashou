"""Certificate fights (owner, 2026-10-23: "so many people are bad at it"). Rules: doc/contributing/certs-style.md.

Every key, CA and certificate is made at setup with openssl, in the arena or next to it: lab keys, no
passphrase, nothing leaves the machine. The Insecure Iguana's server is Python's own, on 127.0.0.1 only,
stopped when the arena closes (the Loopback Lurker's way).
"""

import os
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import Challenge
from .network import alive, background, listening, loopback_works, stop, wait
from .trials import trial
from ..i18n import _

NET = dict(pet="packet", skill="network", tools=("openssl",), requires=["openssl"])
SITES = ["shop", "mail", "wiki", "status", "api", "blog", "git", "chat", "docs", "photos", "music", "files"]
DOMAINS = ["example", "example.org", "example.net", "lab.test"]
WORDS = ["harbor", "lantern", "meadow", "copper", "falcon", "orchard", "glacier", "ember"]
MONTH = 30 * 24 * 3600

# Extensions, one section per kind of certificate: the CA ones can sign, a leaf serves names (its SAN).
EXTENSIONS = """[ca]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
[leaf]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = {san}
"""


def openssl(*args, stdin=None, cwd=None):
    """Run openssl; its output (an error raises: setup can't go on without its files)."""
    done = subprocess.run(["openssl", *map(str, args)], input=stdin, capture_output=True, text=True, timeout=30,
                          cwd=cwd)
    if done.returncode:
        raise RuntimeError(f"openssl {args[0]}: {done.stderr.strip()}")
    return done.stdout


def check(*args):
    """Run openssl on a player's files: (ok, output), never an exception."""
    try:
        done = subprocess.run(["openssl", *map(str, args)], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False, ""
    return done.returncode == 0, done.stdout


def new_key(path):
    """A lab key (ECDSA P-256, no passphrase), readable by its owner only (T5, T6)."""
    openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", path)
    os.chmod(path, 0o600)
    return path


def issue(out, key, cn, rng, issuer=None, days=90, sans=(), pathlen=None):
    """A certificate for `key`: a CA when it has no SAN (with at most `pathlen` CAs below it), a server
    certificate otherwise. Self-signed when issuer (cert, key) is None."""
    with tempfile.TemporaryDirectory(prefix="bashou-cert-") as tmp:
        csr, ext = Path(tmp) / "req.csr", Path(tmp) / "ext.cnf"
        text = EXTENSIONS.format(san=", ".join(f"DNS:{n}" for n in sans) or "DNS:unused.invalid")
        if pathlen is not None:
            text = text.replace("CA:TRUE\n", f"CA:TRUE, pathlen:{pathlen}\n", 1)
        ext.write_text(text)
        openssl("req", "-new", "-key", key, "-subj", f"/CN={cn}", "-out", csr)
        sign = ["-CA", issuer[0], "-CAkey", issuer[1]] if issuer else ["-signkey", key]
        openssl("x509", "-req", "-in", csr, *sign, "-set_serial", rng.getrandbits(62) + 1, "-days", days,
                "-sha256", "-extfile", ext, "-extensions", "leaf" if sans else "ca", "-out", out)
    return out


def lab_ca(folder, rng, cn, issuer=None, pathlen=None):
    """A CA in `folder` (its key next to its certificate): (cert, key)."""
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"\W+", "-", cn.lower())
    key = new_key(folder / f"{slug}.key")
    return issue(folder / f"{slug}.pem", key, cn, rng, issuer=issuer, days=3650, pathlen=pathlen), key


def hidden(work):
    """Next to the arena, not in it: the CA keys and server files players never need."""
    folder = work.parent / "pki"
    folder.mkdir(exist_ok=True)
    return folder


def sites(rng, n):
    domain = rng.choice(DOMAINS)
    return [f"{s}.{domain}" for s in rng.sample(SITES, n)]


def pems(text):
    """The PEM blocks of a file, each without its spaces: what to compare."""
    return ["".join(b.split()) for b in re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                                                  text, re.S)]


def file_answer(folder):
    """An answer that names a file: `api.pem` or `certs/api.pem`."""
    return lambda work, meta, value: value.strip().removeprefix(f"{folder}/") == meta["answer"]


# --- which certificate dies within 30 days -----------------------------------------------------

def expiry_setup(work, rng):
    ca = lab_ca(hidden(work), rng, "Elk Lab CA")
    (work / "certs").mkdir()
    names = sites(rng, 6)
    dying = rng.choice(names)
    for name in names:
        key = new_key(hidden(work) / f"{name}.key")
        days = rng.randint(3, 25) if name == dying else rng.randint(45, 200)
        issue(work / "certs" / f"{name}.pem", key, name, rng, issuer=ca, days=days, sans=[name])
    return {"answer": f"{dying}.pem"}


# --- which site isn't covered by its own certificate ------------------------------------------------

def san_setup(work, rng):
    ca = lab_ca(hidden(work), rng, "Salamander Lab CA")
    (work / "sites").mkdir()
    names = sites(rng, 5)
    bad = rng.choice(names)
    for name in names:
        key = new_key(hidden(work) / f"{name}.key")
        sans = [f"www.{name}"] if name == bad else [name, f"www.{name}"]     # the CN says the site, the SAN doesn't
        issue(work / "sites" / f"{name}.pem", key, name, rng, issuer=ca, sans=sans)
    return {"answer": bad}


def same_site(work, meta, value):
    return value.strip().lower().removesuffix(".pem").removeprefix("sites/") == meta["answer"]


# --- which key goes with server.pem ---------------------------------------------------------------------

def kobold_setup(work, rng):
    ca = lab_ca(hidden(work), rng, "Kobold Lab CA")
    (work / "keys").mkdir()
    names = rng.sample(["old.key", "new.key", "backup.key", "test.key", "spare.key", "2025.key"], 4)
    keys = [new_key(work / "keys" / n) for n in names]
    right = rng.choice(keys)
    site = sites(rng, 1)[0]
    issue(work / "server.pem", right, site, rng, issuer=ca, sans=[site])
    return {"answer": right.name}


# --- the chain the server should send ---------------------------------------------------------------------

def chain_setup(work, rng):
    pki = hidden(work)
    root = lab_ca(pki / "root", rng, "Chameleon Root CA")
    middle = lab_ca(pki / "mid", rng, "Chameleon Intermediate A", issuer=root)
    issuing = lab_ca(pki / "issuing", rng, "Chameleon Intermediate B", issuer=middle)
    other_root = lab_ca(pki / "other", rng, "Lizard Root CA")
    decoy = lab_ca(pki / "decoy", rng, "Lizard Intermediate", issuer=other_root)
    site = sites(rng, 1)[0]
    issue(work / "server.pem", new_key(pki / "server.key"), site, rng, issuer=issuing, sans=[site])
    (work / "certs").mkdir()
    names = rng.sample(["ca1.pem", "ca2.pem", "ca3.pem", "ca4.pem"], 4)
    for name, (cert, _key) in zip(names, [issuing, middle, root, decoy]):
        (work / "certs" / name).write_text(cert.read_text())
    return {"chain": ["server.pem", names[0], names[1]], "root": names[2]}


def chain_verify(work, meta, value):
    """fullchain.pem: the server's certificate, then each issuer in order, and no root (T3)."""
    try:
        found = pems((work / "fullchain.pem").read_text())
        want = [pems((work / n if n == "server.pem" else work / "certs" / n).read_text())[0] for n in meta["chain"]]
    except (OSError, IndexError):
        return False
    return found == want


# --- curl -k in a script ------------------------------------------------------------------------------------

SERVER = """import http.server, ssl, sys
cert, key, port, word = sys.argv[1:]
class Status(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"status: {word}\\n".encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
server = http.server.HTTPServer(("127.0.0.1", int(port)), Status)
tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.minimum_version = ssl.TLSVersion.TLSv1_2
tls.load_cert_chain(cert, key)
server.socket = tls.wrap_socket(server.socket, server_side=True)
server.serve_forever()
"""

FETCH = """#!/usr/bin/env bash
# Prints the status page of the lab server.
# Usage: fetch.sh

die() {{ printf '%s: %s\\n' "${{0##*/}}" "$*" >&2; exit 1; }}

url=https://127.0.0.1:{port}/status
# {why}
page=$(curl -fsS -k -- "$url") || die "cannot fetch $url"
printf '%s\\n' "$page"
"""


def iguana_setup(work, rng):
    pki = hidden(work)
    ca = lab_ca(pki, rng, "Iguana Lab CA")
    (work / "ca.pem").write_text(ca[0].read_text())
    key = new_key(pki / "server.key")
    with tempfile.TemporaryDirectory(prefix="bashou-cert-") as tmp:
        ext = Path(tmp) / "ext.cnf"
        ext.write_text(EXTENSIONS.format(san="IP:127.0.0.1, DNS:localhost"))
        csr = Path(tmp) / "req.csr"
        openssl("req", "-new", "-key", key, "-subj", "/CN=lab server", "-out", csr)
        openssl("x509", "-req", "-in", csr, "-CA", ca[0], "-CAkey", ca[1], "-set_serial", rng.getrandbits(62) + 1,
                "-days", 30, "-sha256", "-extfile", ext, "-extensions", "leaf", "-out", pki / "server.pem")
    (pki / "server.py").write_text(SERVER)
    word = rng.choice(WORDS)
    for _attempt in range(8):
        port = rng.randrange(20000, 40000)
        if listening(port):
            continue
        pid = background([sys.executable, str(pki / "server.py"), str(pki / "server.pem"), str(key), str(port), word])
        if wait(lambda: listening(port), pid) and (time.sleep(0.2) or alive(pid)):
            break
        stop({"pid": pid})
    else:
        raise RuntimeError("no free port on the loopback")
    (work / "fetch.sh").write_text(FETCH.format(port=port, why=_(
        "The certificate check failed, so someone added -k. The lab CA signed the server's certificate: ca.pem.")))
    return {"pid": pid, "word": word}


# -k, --insecure, and -K/--config (a file can say insecure too), anywhere in the script: an array or a
# continued line hides them from a curl line.
INSECURE = re.compile(r"(?<![\w-])(-[a-zA-Z]*[kK][a-zA-Z]*|--insecure|--config)(?![\w-])")


def fetch(work, home):
    """What fetch.sh prints, run from another folder (cron does), with no curl settings from the player's
    home or environment; "" when it fails."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CURL_", "SSL_", "XDG_CONFIG"))}
    try:
        done = subprocess.run(["bash", str(work / "fetch.sh")], cwd=work.parent, capture_output=True, text=True,
                              timeout=15, env={**env, "HOME": home})
    except subprocess.SubprocessError:
        return ""
    return done.stdout if done.returncode == 0 else ""


def iguana_verify(work, meta, value):
    """fetch.sh gets the page with curl, trusting ca.pem, and nothing turns the check off (T1): with another
    CA in ca.pem, it must fail."""
    ca = work / "ca.pem"
    try:
        text = (work / "fetch.sh").read_text().replace("\\\n", " ")
        real = ca.read_bytes()
    except OSError:
        return False
    code = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    if any(INSECURE.search(line) for line in code) or not any("--cacert" in line for line in code):
        return False
    page = f"status: {meta['word']}"
    with tempfile.TemporaryDirectory(prefix="bashou-cert-") as home:
        if page not in fetch(work, home):
            return False
        other = lab_ca(Path(home) / "other", random.Random(), "Other Lab CA")[0]
        try:
            ca.write_text(other.read_text())
            fooled = page in fetch(work, home)
        finally:
            ca.write_bytes(real)
    return not fooled


# --- a key and a CSR with the right names ---------------------------------------------------------------------

def raccoon_setup(work, rng):
    site = sites(rng, 1)[0]
    names = [site, f"www.{site}"]
    return {"args": {"first": names[0], "second": names[1]}, "names": names}


def strong_key(text):
    """T6: ECDSA P-256 or P-384, or RSA with 2048 bits or more, from `openssl pkey -noout -text`."""
    bits = re.search(r"^Private-Key: \((\d+) bit", text, re.M)
    if not bits:
        return False                                    # Ed25519 and others: not for a web certificate today
    if re.search(r"ASN1 OID|NIST CURVE", text):
        return bool(re.search(r"\b(prime256v1|secp384r1)\b", text))
    return "modulus" in text and int(bits.group(1)) >= 2048


def raccoon_verify(work, meta, value):
    """shop.key: strong, only its owner reads it (T5, T6); shop.csr: signed by that key, every name in its SAN
    (T2), no SHA-1 or MD5."""
    key, csr = work / "shop.key", work / "shop.csr"
    try:
        if key.stat().st_mode & 0o077:
            return False
    except OSError:
        return False
    ok_key, key_text = check("pkey", "-in", key, "-passin", "pass:", "-noout", "-text")
    ok_csr, csr_text = check("req", "-in", csr, "-noout", "-text", "-verify")
    if not (ok_key and ok_csr and strong_key(key_text)):
        return False
    _, csr_pub = check("req", "-in", csr, "-noout", "-pubkey")
    _, key_pub = check("pkey", "-in", key, "-passin", "pass:", "-pubout")
    san = re.search(r"Subject Alternative Name:.*?\n\s*(.+)", csr_text)
    names = set(re.findall(r"DNS:([^,\s]+)", san.group(1))) if san else set()
    signature = re.findall(r"Signature Algorithm: (\S+)", csr_text)
    return (csr_pub.strip() == key_pub.strip() != "" and set(meta["names"]) <= names
            and signature and not any(re.search(r"md5|sha1(?!\d)", a, re.I) for a in signature))


# --- a CA that allows fewer CAs below it than there are ------------------------------------------------------

def panther_setup(work, rng):
    pki = hidden(work)
    root = lab_ca(pki, rng, "Panther Root CA")
    (work / "root.pem").write_text(root[0].read_text())
    culprit = rng.randrange(2)                    # the first or second CA: one with CAs below it (2, then 1)
    limits = [None, None, 0]                      # the last CA signs servers only: pathlen:0 is right there (the trap)
    limits[culprit] = rng.randrange(2 - culprit)  # fewer than the CAs below it
    names = rng.sample(["ca1.pem", "ca2.pem", "ca3.pem"], 3)
    cns = rng.sample(["Jungle CA", "Night CA", "Shadow CA", "Canopy CA", "Moonlight CA"], 3)
    (work / "certs").mkdir()
    issuer = root
    for i in range(3):
        issuer = lab_ca(pki / f"ca{i}", rng, cns[i], issuer=issuer, pathlen=limits[i])
        (work / "certs" / names[i]).write_text(issuer[0].read_text())
    site = sites(rng, 1)[0]
    issue(work / "leaf.pem", new_key(pki / "leaf.key"), site, rng, issuer=issuer, sans=[site])
    return {"answer": names[culprit]}


# --- a certificate signed by a server's certificate --------------------------------------------------------

def ibex_setup(work, rng):
    pki = hidden(work)
    root = lab_ca(pki, rng, "Ibex Root CA")
    middle = lab_ca(pki, rng, "Ibex Intermediate CA", issuer=root)
    (work / "ca.pem").write_text(root[0].read_text())
    names = sites(rng, 5)
    signer = rng.choice(names)
    fake = rng.choice([n for n in names if n != signer])
    (work / "sites").mkdir()
    keys = {n: new_key(pki / f"{n}.key") for n in names}
    for name in [signer] + [n for n in names if n != signer]:
        by = (work / "sites" / f"{signer}.pem", keys[signer]) if name == fake else middle
        issue(work / "sites" / f"{name}.pem", keys[name], name, rng, issuer=by, sans=[name])
    # what the servers send with their certificate: the intermediate, and (the Ibex's doing) the signer's own
    (work / "chain.pem").write_text(middle[0].read_text() + (work / "sites" / f"{signer}.pem").read_text())
    return {"answer": fake}


# --- openssl.cnf: the section that makes an intermediate CA ------------------------------------------------

LAB_CNF = """# The lab's openssl configuration: a section is a [ name ], then one name = value per line.
# openssl x509 -req ... -extfile lab.cnf -extensions v3_intermediate signs an intermediate CA with it.

[ v3_intermediate ]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid

[ server ]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = serverAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid
"""


def cobra_setup(work, rng):
    (work / "lab.cnf").write_text(LAB_CNF)
    return {}


def cobra_verify(work, meta, value):
    """Bashou signs an intermediate with the player's [ v3_intermediate ]: a CA (critical), able to sign a server
    certificate, and refused as soon as another CA sits below it (pathlen:0) (T14)."""
    cnf = work / "lab.cnf"
    if not cnf.is_file():
        return False
    with tempfile.TemporaryDirectory(prefix="bashou-cert-") as tmp:
        t, rng = Path(tmp), random.Random()
        try:
            root = lab_ca(t / "root", rng, "Check Root CA")
            key = new_key(t / "mid.key")
            openssl("req", "-new", "-key", key, "-subj", "/CN=Cobra Intermediate CA", "-out", t / "mid.csr")
            openssl("x509", "-req", "-in", t / "mid.csr", "-CA", root[0], "-CAkey", root[1], "-set_serial", 2,
                    "-days", 30, "-sha256", "-extfile", cnf, "-extensions", "v3_intermediate", "-out", t / "mid.pem")
            middle = (t / "mid.pem", key)
            leaf = issue(t / "leaf.pem", new_key(t / "leaf.key"), "shop.example", rng, issuer=middle,
                         sans=["shop.example"])
            below = lab_ca(t / "below", rng, "Below CA", issuer=middle)
            deeper = issue(t / "deeper.pem", new_key(t / "deeper.key"), "shop.example", rng, issuer=below,
                           sans=["shop.example"])
        except (RuntimeError, OSError, subprocess.SubprocessError):
            return False
        _, text = check("x509", "-in", middle[0], "-noout", "-text")
        (t / "both.pem").write_text(middle[0].read_text() + below[0].read_text())
        signs, _ = check("verify", "-CAfile", root[0], "-untrusted", middle[0], leaf)
        too_deep, _ = check("verify", "-CAfile", root[0], "-untrusted", t / "both.pem", deeper)
    return (bool(re.search(r"Basic Constraints: critical\s*\n\s*CA:TRUE, pathlen:0\b", text))
            and bool(re.search(r"Key Usage: critical\s*\n\s*.*Certificate Sign.*CRL Sign", text))
            and signs and not too_deep)


# --- revocation: a small CA run with openssl ca -------------------------------------------------------------

CA_CNF = """# The lab CA. openssl ca -config ca.cnf reads this file; run it from this folder.
[ ca ]
default_ca = lab

[ lab ]
dir              = ./pki
certificate      = ./ca.pem
private_key      = $dir/ca.key
database         = $dir/index.txt
serial           = $dir/serial
crlnumber        = $dir/crlnumber
new_certs_dir    = $dir/newcerts
default_md       = sha256
default_days     = 90
default_crl_days = 7
policy           = only_cn
copy_extensions  = copy
x509_extensions  = server

[ only_cn ]
commonName = supplied

[ server ]
basicConstraints = critical, CA:FALSE
keyUsage         = critical, digitalSignature
extendedKeyUsage = serverAuth
"""


def ca_folder(folder, rng, cn, names, keys):
    """A CA run by `openssl ca` (ca.cnf, ca.pem, pki/), which issued certs/<name>.pem for each name."""
    pki = folder / "pki"
    (pki / "newcerts").mkdir(parents=True)
    (pki / "index.txt").write_text("")
    (pki / "serial").write_text(f"{rng.randrange(0x1000, 0xF000):04X}\n")
    (pki / "crlnumber").write_text("01\n")
    (folder / "ca.cnf").write_text(CA_CNF)
    issue(folder / "ca.pem", new_key(pki / "ca.key"), cn, rng, days=3650)
    (folder / "certs").mkdir()
    for name in names:
        key = new_key(keys / f"{name}.key")
        openssl("req", "-new", "-key", key, "-subj", f"/CN={name}", "-addext", f"subjectAltName=DNS:{name}",
                "-out", keys / f"{name}.csr")
        run_ca(folder, "-notext", "-in", keys / f"{name}.csr", "-out", folder / "certs" / f"{name}.pem")


def run_ca(folder, *args):
    return openssl("ca", "-batch", "-config", "ca.cnf", *args, cwd=folder)


def serial_of(cert):
    _, out = check("x509", "-in", cert, "-noout", "-serial")
    return int(out.strip().split("=")[-1] or "0", 16)


def revoked(crl):
    """{serial: what the CRL says about it} of a CRL file."""
    _, text = check("crl", "-in", crl, "-noout", "-text")
    return {int(s, 16): body for s, body in
            re.findall(r"Serial Number: ([0-9A-Fa-f]+)(.*?)(?=Serial Number:|Signature Algorithm|\Z)", text, re.S)}


def reindeer_setup(work, rng):
    names = sites(rng, 3)
    ca_folder(work, rng, "Reindeer Lab CA", names, hidden(work))
    run_ca(work, "-gencrl", "-out", work / "crl.pem")
    leaked = rng.choice(names)
    return {"args": {"site": leaked}, "leaked": leaked}


def reindeer_verify(work, meta, value):
    """crl.pem: signed by the lab CA, revoking the leaked certificate and only it, for keyCompromise (T15)."""
    signed, _ = check("crl", "-in", work / "crl.pem", "-CAfile", work / "ca.pem", "-noout")
    if not signed:
        return False
    listed = revoked(work / "crl.pem")
    serial = serial_of(work / "certs" / f"{meta['leaked']}.pem")
    return set(listed) == {serial} and "Key Compromise" in listed[serial]


# --- the Sage Owl's chest: who signed it ----------------------------------------------------------------------

def chest_setup(work, rng):
    name = rng.choice(["Sage Owl CA", "Old Oak CA", "Moonlit Library CA", "Quiet Hill CA"])
    ca = lab_ca(hidden(work), rng, name)
    site = sites(rng, 1)[0]
    issue(work / "site.pem", new_key(hidden(work) / "site.key"), site, rng, issuer=ca, sans=[site])
    return {"answer": name}


def same_issuer(work, meta, value):
    return value.strip().removeprefix("issuer=").strip().removeprefix("/").removeprefix("CN=").removeprefix("CN = ").strip().lower() == \
        meta["answer"].lower()


# --- the fights -----------------------------------------------------------------------------------------------

ALL = [
    Challenge(level=1, id="expiry_elk", threat="Expiry Elk",
              task="The Expiry Elk keeps six certificates in certs/. One of them stops working within 30 days.\n"
                   "Which file? answer <file>",
              help="Look for how openssl x509 shows the dates of a certificate.",
              hints=["openssl x509 -in FILE -noout -enddate prints the date a certificate stops working "
                     "(notAfter). -checkend 2592000 asks: still valid in 30 days (2,592,000 seconds)? "
                     "Its exit status says no with 1.",
                     "for f in certs/*.pem; do openssl x509 -in \"$f\" -noout -checkend 2592000 > /dev/null "
                     "|| echo \"$f\"; done"],
              setup=expiry_setup, verify=file_answer("certs"), **NET),
    Challenge(level=2, id="san_salamander", threat="SAN Salamander", after=("expiry_elk",),
              task="The SAN Salamander swapped names in sites/: each certificate is named after the site that "
                   "serves it.\nOne of them doesn't cover its own site, so browsers refuse it. Which site? "
                   "answer <site>",
              hints=["Browsers only read the Subject Alternative Name (SAN), the list of names a certificate "
                     "covers: the CN in its subject doesn't count. openssl x509 -in FILE -noout -ext "
                     "subjectAltName shows that list (a Mac's LibreSSL has no -ext: use -text, and read the line "
                     "under Subject Alternative Name).",
                     "for f in sites/*.pem; do openssl x509 -in \"$f\" -noout -checkhost \"$(basename \"$f\" "
                     ".pem)\"; done (a Mac's LibreSSL has no -checkhost: read the line under Subject Alternative "
                     "Name in -text instead)"],
              setup=san_setup, verify=same_site, **NET),
    Challenge(level=2, id="key_kobold", threat="Key Kobold",
              task="The Key Kobold hid server.pem's private key among the keys in keys/.\n"
                   "Which key goes with server.pem? answer <file>",
              hints=["A certificate holds a public key, and its private key is the other half. "
                     "openssl x509 -in server.pem -noout -pubkey prints the certificate's public key; "
                     "openssl pkey -in KEY -pubout prints the public half of a private key. "
                     "The right pair prints the same lines.",
                     "c=$(openssl x509 -in server.pem -noout -pubkey); for k in keys/*; do "
                     "[ \"$(openssl pkey -in \"$k\" -pubout)\" = \"$c\" ] && echo \"$k\"; done"],
              setup=kobold_setup, verify=file_answer("keys"), **NET),
    Challenge(level=3, id="chain_chameleon", threat="Chain Chameleon", fix=True, after=("key_kobold",),
              task="The Chain Chameleon mixed up certs/. The server sends only server.pem, so clients can't link "
                   "it to the root they trust.\nWrite fullchain.pem: server.pem first, then the intermediates in "
                   "order, without the root. Then: verify",
              hints=["Each certificate names its issuer: openssl x509 -in FILE -noout -subject -issuer. Start from "
                     "server.pem, find the file whose subject is its issuer, and go on up to the root (its subject "
                     "and issuer are the same). Clients already have the root: it stays out. One file belongs to "
                     "another chain.",
                     "cat server.pem certs/A.pem certs/B.pem > fullchain.pem (A issued server.pem, B issued A). "
                     "openssl verify -CAfile certs/ROOT.pem -untrusted fullchain.pem fullchain.pem checks that the "
                     "links exist, not their order: the order is yours (each file's issuer is the next file's "
                     "subject)."],
              setup=chain_setup, verify=chain_verify, **NET),
    Challenge(level=2, id="insecure_iguana", threat="Insecure Iguana", fix=True, os="linux", after=("chain_chameleon",),
              task="The Insecure Iguana got into fetch.sh: someone \"fixed\" a certificate error with curl -k, "
                   "which turns the check off.\nMake fetch.sh trust the lab's CA (ca.pem, next to the script) instead, without -k. "
                   "It must work from any folder: cron runs it from elsewhere. Then: verify",
              hints=["-k (--insecure) makes curl accept any certificate, an attacker's too, and it stays in the "
                     "script forever. The real fix: tell curl which CA signed the server's certificate. "
                     "--cacert FILE trusts that CA for this one command.",
                     "In fetch.sh, add the line dir=$(dirname -- \"${BASH_SOURCE[0]}\") (the script's own folder: a script "
                     "can't count on the folder it's run from), replace -k with --cacert \"$dir/ca.pem\", then run: "
                     "bash fetch.sh"],
              setup=iguana_setup, verify=iguana_verify, cleanup=stop, works=loopback_works,
              pet="packet", skill="network", tools=("openssl", "curl"), requires=["openssl", "curl"]),
    Challenge(level=3, id="request_raccoon", threat="Request Raccoon", fix=True, after=("san_salamander",),
              task="The Request Raccoon wants a certificate for {first} and {second}.\nMake a private key shop.key "
                   "(ECDSA P-256, or RSA 2048 bits or more) that only you can read, and a request shop.csr whose "
                   "SAN holds both names. Then: verify",
              hints=["openssl req -new makes a CSR (certificate signing request): your public key and the names, "
                     "signed with your key, for a CA to sign. -newkey makes the key at the same time, -noenc leaves "
                     "it without a passphrase (fine for a lab), -addext adds the SAN. A CN alone covers nothing. "
                     "On a Mac's LibreSSL: -newkey rsa:2048 -nodes instead of the ec, -pkeyopt and -noenc part.",
                     "(umask 077 && openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -noenc -keyout "
                     "shop.key -out shop.csr -subj '/CN={first}' -addext 'subjectAltName=DNS:{first},DNS:{second}') "
                     "(umask 077: the key is made readable by you only, from its first moment)"],
              setup=raccoon_setup, verify=raccoon_verify, **NET),
    Challenge(level=3, id="pathlen_panther", threat="Pathlen Panther", after=("chain_chameleon",),
              task="The Pathlen Panther broke a chain: leaf.pem is refused now, though every file in certs/ is a "
                   "CA.\nOne of them allows fewer CAs below it than there are. Which file? answer <file>",
              help="Look for what openssl verify prints when a chain fails, and how a CA says how deep it goes.",
              hints=["A CA's basicConstraints can hold pathlen: how many CAs may come below it. pathlen:0 means "
                     "server certificates only, no CA below. openssl x509 -in FILE -noout -ext basicConstraints "
                     "shows it (a Mac's LibreSSL has no -ext: read Basic Constraints in -text).",
                     "cat certs/*.pem > all.pem; openssl verify -CAfile root.pem -untrusted all.pem leaf.pem (the "
                     "line above the error names the CA), then find its file: for f in certs/*.pem; do echo "
                     "\"$f\"; openssl x509 -in \"$f\" -noout -subject; done"],
              setup=panther_setup, verify=file_answer("certs"), **NET),
    Challenge(level=2, id="impostor_ibex", threat="Impostor Ibex", after=("chain_chameleon",),
              task="The Impostor Ibex made one of the certificates in sites/ itself: it signed it with a server's "
                   "certificate, not a CA.\nca.pem is the root, chain.pem holds what the servers send. Which site? "
                   "answer <site>",
              hints=["Only a CA may sign certificates: its basicConstraints says CA:TRUE and its keyUsage holds "
                     "keyCertSign. A server's certificate says CA:FALSE. openssl verify follows each signature up to "
                     "the root and checks that every signer is a CA.",
                     "for f in sites/*.pem; do openssl verify -CAfile ca.pem -untrusted chain.pem \"$f\"; done "
                     "(look for invalid CA certificate: the line above it names the signer, the refused file is the "
                     "answer)"],
              setup=ibex_setup, verify=same_site, **NET),
    Challenge(level=3, id="config_cobra", threat="Config Cobra", fix=True, after=("pathlen_panther",),
              task="The Config Cobra bit lab.cnf: its [ v3_intermediate ] section makes an intermediate CA that "
                   "can't sign anything.\nFix that section: a CA (basicConstraints critical) that may sign server "
                   "certificates but no other CA, with the key usages a CA needs. Then: verify (Bashou signs an "
                   "intermediate with your section and tries it)",
              hints=["In a section, each line is name = value. basicConstraints = critical, CA:TRUE, pathlen:N: a "
                     "CA with at most N CAs below it. keyUsage = critical, keyCertSign, cRLSign: it may sign "
                     "certificates and revocation lists. digitalSignature alone is a server's.",
                     "Under [ v3_intermediate ]: basicConstraints = critical, CA:TRUE, pathlen:0 and keyUsage = "
                     "critical, keyCertSign, cRLSign"],
              setup=cobra_setup, verify=cobra_verify, **NET),
    Challenge(level=3, id="revoked_reindeer", threat="Revoked Reindeer", fix=True, after=("config_cobra",),
              task="The Revoked Reindeer stole a key: the key of {site} leaked, so its certificate must stop being "
                   "trusted now, not at its end date.\nYou run the lab CA (ca.cnf, from this folder): revoke "
                   "certs/{site}.pem with the reason keyCompromise, and publish a new CRL as crl.pem. Then: verify",
              hints=["openssl ca -config ca.cnf runs the CA. -revoke FILE marks the certificate R (revoked) in "
                     "pki/index.txt, and -crl_reason says why. Clients never read index.txt: they read the CRL "
                     "(certificate revocation list), which -gencrl makes from it, signed by the CA.",
                     "openssl ca -config ca.cnf -revoke certs/{site}.pem -crl_reason keyCompromise, then: openssl ca "
                     "-config ca.cnf -gencrl -out crl.pem. Check it: openssl crl -in crl.pem -noout -text"],
              setup=reindeer_setup, verify=reindeer_verify, **NET),
]

CHEST = trial("trial_cert_issuer", 1, "This chest holds site.pem, a certificate. Who signed it? answer <issuer>",
              ["Every certificate names who signed it: its issuer. openssl x509 -in site.pem -noout -issuer "
               "prints it, after issuer= and CN= (on a Mac: issuer= /CN=).", "openssl x509 -in site.pem -noout -issuer"],
              chest_setup, same_issuer, requires=["openssl"], teaches=["openssl"])
def crl_chest_setup(work, rng):
    names = sites(rng, 3)
    folder = Path(tempfile.mkdtemp(prefix="ca-", dir=hidden(work)))
    ca_folder(folder, rng, "Sage Owl CA", names, hidden(work))
    gone = rng.choice(names)
    run_ca(folder, "-revoke", folder / "certs" / f"{gone}.pem", "-crl_reason", "superseded")
    run_ca(folder, "-gencrl", "-out", work / "crl.pem")
    return {"answer": serial_of(folder / "certs" / f"{gone}.pem")}


def same_serial(work, meta, value):
    said = value.strip().lower().removeprefix("serial=").removeprefix("0x").replace(":", "").strip()
    try:
        return int(said, 16) == meta["answer"]
    except ValueError:
        return False


CRL_CHEST = trial("trial_crl_serial", 2, "This chest holds crl.pem, a revocation list. Which serial number does it "
                  "revoke? answer <serial>",
                  ["A CRL (certificate revocation list) holds the serial numbers of the certificates its CA revoked, "
                   "signed by that CA. openssl crl -in crl.pem -noout -text prints them, under Revoked Certificates.",
                   "openssl crl -in crl.pem -noout -text"],
                  crl_chest_setup, same_serial, requires=["openssl"], teaches=["openssl"])
CHESTS = [CHEST, CRL_CHEST]       # locked chests in `bashou adventure`
