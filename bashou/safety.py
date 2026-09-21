"""Risky commands: your pet warns you, and running enough of them attracts the Gremlin."""

import random
import re

# id: (pattern, warnings)
RISKS = {
    # A download run straight by a shell: `curl … | sh`, `wget -O- … | sudo bash`,
    # `bash <(curl …)`, `sh -c "$(curl …)"`.
    "remote_script": (re.compile(r"""
        \b(curl|wget)\b[^|;&]*\|\s*(sudo\s+(-\S+\s+)*)?(env\s+)?\S*?\b(ba|z|da|k|fi)?sh\b
      | \b(ba|z|da|k)?sh\s+(-\S+\s+)*(<\(|["']?\$\()\s*(curl|wget)\b
    """, re.X), [
        "Careful! That ran a script from the internet unread. Download it, read it, then run it.",
        "A download piped into a shell runs whatever the server sends. "
        "Save it first: curl -fsSLo install.sh URL && less install.sh",
        "Did you read that script first? Whoever controls the URL controls your shell.",
    ]),
    "chmod_777": (re.compile(r"\bchmod\s+(-\S+\s+)*(0?777|a\+rwx|ugo\+rwx)\b"), [
        "chmod 777 lets every user change that file. u+x (or 755) is usually enough.",
    ]),
    "insecure_tls": (re.compile(r"\bcurl\b[^|;&]*\s(-[a-zA-Z]*k[a-zA-Z]*|--insecure)\b|\bwget\b[^|;&]*--no-check-certificate"), [
        "That skipped the HTTPS check: anyone in the middle could swap the download.",
    ]),
    "rm_everything": (re.compile(
        r"\brm\s+(-\S+\s+)*(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\s+(-\S+\s+)*"
        r"(/|/\*|~|~/|~/\*|\$HOME|\$HOME/|\"\$HOME\"|\"\$HOME\"/)(\s|;|$)"), [
        "rm -r on / or ~ deletes everything you have. Always double-check that path!",
    ]),
    "no_host_check": (re.compile(r"StrictHostKeyChecking=no"), [
        "Without host key checks, you won't notice if someone swaps the server.",
    ]),
    "sudo_pip": (re.compile(r"\bsudo\s+(-\S+\s+)*(python3?\s+-m\s+)?pip3?\s+install\b"), [
        "sudo pip can break the system's Python. Use a venv, or pip install --user.",
    ]),
    "sshpass": (re.compile(r"\bsshpass\s+-p\b"), [
        "A password typed in a command stays in your history. SSH keys are safer.",
    ]),
}
SUDO = "…and with sudo, it could change anything on your machine."


def risk(command):
    """Id of the first risk found in a command line, or None."""
    for rid, (pattern, _warnings) in RISKS.items():
        if pattern.search(command):
            return rid
    return None


def warning(command, rng=random):
    """English sentences warning about a risky command (translate each one), or []."""
    rid = risk(command)
    if not rid:
        return []
    parts = [rng.choice(RISKS[rid][1])]
    if rid == "remote_script" and re.search(r"\bsudo\b", command):
        parts.append(SUDO)
    return parts


def messages():
    return [w for _pattern, warnings in RISKS.values() for w in warnings] + [SUDO]
