"""The reference answer of the Drop Dragon, found another way than the fight's own code: read rules.nft
like nft does, top to bottom, and print the line of the first rule with a verdict that matches the packet.

    python3 nft_first_match.py rules.nft 198.51.100.7 to TCP port 8080
"""

import ipaddress
import re
import sys

RULE = re.compile(r"^\s*(?:ip saddr (\S+) )?tcp dport (\{[^}]*\}|\S+) (accept|drop|reject)\b")


def ports_match(ports, port):
    for p in ports.strip("{} ").replace(" ", "").split(","):
        low, _, high = p.partition("-")
        if int(low) <= port <= int(high or low):
            return True
    return False


def first_match(lines, source, port):
    for n, line in enumerate(lines, 1):
        m = RULE.match(line)
        if m and (not m[1] or source in ipaddress.ip_network(m[1])) and ports_match(m[2], port):
            return n
    return None


if __name__ == "__main__":
    path, source, port = sys.argv[1], ipaddress.ip_address(sys.argv[2]), int(sys.argv[-1])
    with open(path) as f:
        print(first_match(f, source, port))
