"""Network fights (owner, 2026-09-25): IPv4, IPv6, DNS and TCP, and nothing ever leaves the machine.

Three kinds, all offline:
- the player's own machine, read-only: `ip addr`, `ip route get` (asks the kernel, sends nothing), `getent`;
- captures written here as bytes, read with `tcpdump -r` (no root needed to read a file);
- a listener started for the fight, bound to 127.0.0.1 or ::1 only, stopped when the arena closes (the
  Process Phantom's way): it can't be reached from any other machine.
"""

import ipaddress
import os
import shlex
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

from . import Challenge

NET = dict(pet="pigeon", skill="network")
TCPDUMP = dict(tools=("tcpdump", "tshark"), requires=["tcpdump"])


def run(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def route(target):
    """What `ip route get` says about one address: {"via", "dev", "src"} (no packet is sent)."""
    words = run(["ip", "route", "get", target]).split()
    return {k: words[words.index(k) + 1] for k in ("via", "dev", "src") if k in words[:-1]}


def ipv4_of(dev):
    return [line.split()[3].split("/")[0] for line in run(["ip", "-4", "-o", "addr", "show", "dev", dev]).splitlines()
            if len(line.split()) > 3]


# --- listeners on the loopback --------------------------------------------------------------------

def sockets(v6=False):
    """(local port, remote port, state) of every TCP socket, from /proc (what ss reads too)."""
    found = []
    try:
        lines = Path(f"/proc/net/tcp{'6' if v6 else ''}").read_text().splitlines()[1:]
    except OSError:
        return found
    for line in lines:
        f = line.split()
        (local, lport), (_remote, rport) = f[1].split(":"), f[2].split(":")
        found.append((local, int(lport, 16), int(rport, 16), f[3]))
    return found


LOOPBACK4, LOOPBACK6 = "0100007F", "00000000000000000000000001000000"


def listening(port, v6=False):
    """Is something listening on this port, on the loopback address only?"""
    return any(lp == port and st == "0A" and addr == (LOOPBACK6 if v6 else LOOPBACK4)
               for addr, lp, _rp, st in sockets(v6))


def background(argv):
    """Start argv detached from Python (cleanup() stops it); its PID."""
    out = subprocess.run(["bash", "-c", f"{shlex.join(argv)} </dev/null >/dev/null 2>&1 & echo $!"],
                         capture_output=True, text=True)
    return int(out.stdout)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def wait(ready, pid, seconds=5.0):
    end = time.time() + seconds
    while time.time() < end and alive(pid):
        if ready():
            return True
        time.sleep(0.05)
    return False


def serve(work, rng, address="127.0.0.1"):
    """A small web server on the loopback, on a free random port: (port, pid)."""
    www = work.parent / "www"                           # outside the arena folder: nothing to see there
    www.mkdir(exist_ok=True)
    v6 = ":" in address
    for _ in range(8):
        port = rng.randrange(20000, 40000)
        if listening(port, v6) or listening(port, not v6):
            continue                                    # taken: another program's, not ours
        pid = background([sys.executable, "-m", "http.server", "--bind", address, "--directory", str(www), str(port)])
        if wait(lambda: listening(port, v6), pid) and (time.sleep(0.2) or alive(pid)):   # it didn't die on bind
            return port, pid
        stop({"pid": pid})
    raise RuntimeError("no free port on the loopback")


def stop(meta):
    try:
        os.kill(meta["pid"], signal.SIGTERM)
    except (OSError, KeyError):
        pass


def loopback_works():
    return Path("/proc/net/tcp").exists()


def lurker_setup(work, rng):
    port, pid = serve(work, rng)
    return {"args": {"pid": pid}, "answer": port, "pid": pid}


# The Established Ettin: a server and its own clients, all on 127.0.0.1, connections held open.
ETTIN = ("import socket, sys, time\n"
         "port, n = int(sys.argv[1]), int(sys.argv[2])\n"
         "server = socket.socket()\n"
         "server.bind(('127.0.0.1', port))\n"
         "server.listen(16)\n"
         "clients = [socket.create_connection(('127.0.0.1', port)) for _ in range(n)]\n"
         "accepted = [server.accept() for _ in range(n)]\n"
         "time.sleep(3600)\n")


def ettin_setup(work, rng):
    n = rng.randrange(3, 9)
    for _ in range(8):
        port = rng.randrange(20000, 40000)
        if any(lp == port or rp == port for _a, lp, rp, _s in sockets()):
            continue
        pid = background([sys.executable, "-c", ETTIN, str(port), str(n)])
        if wait(lambda: sum(rp == port and st == "01" for _a, _lp, rp, st in sockets()) == n, pid):
            return {"args": {"port": port}, "answer": n, "pid": pid}
        stop({"pid": pid})
    raise RuntimeError("no free port on the loopback")


# --- the machine's own addresses, routes and names --------------------------------------------------

def gateway_works():
    return "via" in route("192.0.2.1")


def adder_setup(work, rng):
    dev = route("192.0.2.1").get("dev", "lo")
    return {"args": {"dev": dev}, "answer": (ipv4_of(dev) or ["?"])[0], "addrs": ipv4_of(dev)}


def raven_setup(work, rng):
    target = f"{rng.choice(['198.51.100', '203.0.113'])}.{rng.randrange(1, 255)}"
    return {"args": {"target": target}, "answer": route(target).get("via", "?")}


def own_name():
    return os.uname().nodename


def names_of(name):
    """Every address programs may get for the name (hosts gives the first one, ahosts them all)."""
    lines = run(["getent", "hosts", name]).splitlines() + run(["getent", "ahosts", name]).splitlines()
    return sorted({line.split()[0] for line in lines if line.split()})


def rook_setup(work, rng):
    name = own_name()
    return {"args": {"name": name}, "answer": (names_of(name) or ["?"])[0], "addrs": names_of(name)}


# --- address files ----------------------------------------------------------------------------------

def sprite_setup(work, rng):
    third = rng.randrange(0, 60) * 4
    net = ipaddress.ip_network(f"10.{rng.randrange(1, 250)}.{third}.0/22")
    first, last = int(net.network_address), int(net.broadcast_address)
    inside = [ipaddress.ip_address(rng.randrange(first + 1, last)) for _ in range(rng.randrange(5, 12))]
    near = [ipaddress.ip_address(first - rng.randrange(1, 300)) for _ in range(4)] + \
           [ipaddress.ip_address(last + rng.randrange(1, 300)) for _ in range(5)]
    hosts = inside + near
    rng.shuffle(hosts)
    (work / "hosts.txt").write_text("".join(f"{h}\n" for h in hosts))
    return {"args": {"net": str(net)}, "answer": sum(h in net for h in hosts)}


def serpent_setup(work, rng):
    pick = [ipaddress.IPv6Address(rng.getrandbits(64) | (0x20010db8 << 96)) for _ in range(6)]
    pick += [ipaddress.IPv6Address("fe80::" + ":".join(f"{rng.randrange(1, 0xffff):x}" for _ in range(4))),
             ipaddress.IPv6Address(f"fd{rng.randrange(0, 256):02x}:{rng.randrange(0, 0xffff):x}::{rng.randrange(1, 0xffff):x}")]
    twin = ipaddress.IPv6Address((0x20010db8 << 96) | (rng.randrange(1, 0xffff) << 32) | rng.randrange(1, 0xffff))
    long_form = twin.exploded                                  # all 32 digits
    lines = [str(a) for a in pick] + [str(twin), long_form]
    rng.shuffle(lines)
    (work / "addrs.txt").write_text("".join(f"{a}\n" for a in lines))
    return {"answer": str(twin)}


# --- captures: pcap files written byte by byte ----------------------------------------------------

SYN, RST, PSH, ACK = 0x02, 0x04, 0x08, 0x10


def checksum(data):
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xffff) + (total >> 16)
    return ~total & 0xffff


def ipv4(src, dst, proto, payload):
    head = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), 0, 0x4000, 64, proto, 0,
                       ipaddress.IPv4Address(src).packed, ipaddress.IPv4Address(dst).packed)
    head = head[:10] + struct.pack("!H", checksum(head)) + head[12:]
    return b"\x02\x00\x00\x00\x00\x01\x02\x00\x00\x00\x00\x02\x08\x00" + head + payload   # Ethernet, then IP


def pseudo(src, dst, proto, segment):
    return ipaddress.IPv4Address(src).packed + ipaddress.IPv4Address(dst).packed + struct.pack("!BBH", 0, proto, len(segment))


def tcp(src, sport, dst, dport, flags, seq=0, ack=0):
    seg = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 5 << 4, flags, 64240, 0, 0)
    seg = seg[:16] + struct.pack("!H", checksum(pseudo(src, dst, 6, seg) + seg)) + seg[18:]
    return ipv4(src, dst, 6, seg)


def udp(src, sport, dst, dport, data):
    seg = struct.pack("!HHHH", sport, dport, 8 + len(data), 0) + data
    seg = seg[:6] + struct.pack("!H", checksum(pseudo(src, dst, 17, seg) + seg) or 0xffff) + seg[8:]
    return ipv4(src, dst, 17, seg)


def pcap(path, packets):
    """packets: (seconds, frame). A classic pcap file (Ethernet), as tcpdump -w writes it."""
    out = [struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)]
    for t, frame in sorted(packets, key=lambda p: p[0]):
        out.append(struct.pack("<IIII", int(t), int((t % 1) * 1e6), len(frame), len(frame)) + frame)
    Path(path).write_bytes(b"".join(out))


START = 1790000000.0


def handshake(packets, t, client, cport, server, sport, rng, answer=True, finish=True):
    """One connection attempt: SYN, then SYN-ACK and ACK (or silence, or RST)."""
    seq = rng.getrandbits(32)
    packets.append((t, tcp(client, cport, server, sport, SYN, seq)))
    if answer is None:                                        # nobody answers: the client retries
        packets += [(t + 1, tcp(client, cport, server, sport, SYN, seq)), (t + 3, tcp(client, cport, server, sport, SYN, seq))]
        return
    if answer == "rst":
        packets.append((t + 0.0004, tcp(server, sport, client, cport, RST | ACK, 0, seq + 1)))
        return
    sseq = rng.getrandbits(32)
    packets.append((t + 0.02, tcp(server, sport, client, cport, SYN | ACK, sseq, seq + 1)))
    if finish:
        packets.append((t + 0.04, tcp(client, cport, server, sport, ACK, seq + 1, sseq + 1)))


def heron_setup(work, rng):
    server, packets = "10.0.0.1", []
    ports = rng.sample(range(40000, 60000), rng.randrange(4, 8))
    broken = rng.choice(ports)
    for i, port in enumerate(ports):
        client = f"10.0.0.{rng.randrange(2, 250)}"
        handshake(packets, START + i * 0.7 + rng.random() / 3, client, port, server, 443, rng,
                  answer=None if port == broken else True)
    pcap(work / "capture.pcap", packets)
    return {"answer": broken}


def revenant_setup(work, rng):
    client, server, packets = "10.0.0.5", "10.0.0.1", []
    services = rng.sample([22, 25, 80, 443, 3306, 5432, 6379, 8080, 8443, 9000], 6)
    refused, dropped = services[0], services[1]
    rng.shuffle(services)
    for i, port in enumerate(services):
        handshake(packets, START + i * 0.5, client, rng.randrange(40000, 60000), server, port, rng,
                  answer="rst" if port == refused else None if port == dropped else True)
    pcap(work / "capture.pcap", packets)
    return {"answer": refused}


NAMES = ["wiki", "mail", "shop", "status", "cdn", "api", "docs", "git", "files", "chat", "vpn", "news"]
DOMAINS = ["example.org", "example.com", "example.net"]


def dns_name(name):
    return b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"


def dns_setup(work, rng):
    client, resolver, packets = "10.0.0.5", "10.0.0.53", []
    names = [f"{n}.{rng.choice(DOMAINS)}" for n in rng.sample(NAMES, 7)]
    nx = names[0].replace("example", rng.choice(["exmaple", "exampel", "examlpe"]))   # a typo: no such domain
    fail = names[1]
    names[0] = nx
    order = names[:]
    rng.shuffle(order)
    replies = []
    for i, name in enumerate(order):
        qid, sport, t = rng.randrange(1, 0xffff), rng.randrange(40000, 60000), START + i * 0.3
        question = dns_name(name) + struct.pack("!HH", 1, 1)
        packets.append((t, udp(client, sport, resolver, 53, struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0) + question)))
        if name == nx:
            body = struct.pack("!HHHHHH", qid, 0x8183, 1, 0, 0, 0) + question
        elif name == fail:
            body = struct.pack("!HHHHHH", qid, 0x8182, 1, 0, 0, 0) + question
        else:
            answer = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 3600, 4) + ipaddress.IPv4Address(
                f"203.0.113.{rng.randrange(1, 255)}").packed
            body = struct.pack("!HHHHHH", qid, 0x8180, 1, 1, 0, 0) + question + answer
        replies.append((t + 0.05 + rng.random() * 1.2, udp(resolver, 53, client, sport, body)))
    pcap(work / "dns.pcap", packets + replies)
    return {"answer": nx}


def same_name(work, meta, value):
    return value.strip().rstrip(".").lower() == meta["answer"]


def port_answer(work, meta, value):
    """A port, alone or at the end of an address (10.0.0.5.51522, 10.0.0.5:51522)."""
    last = value.strip().replace(":", ".").split(".")[-1]
    return last == str(meta["answer"])


# --- the fights -------------------------------------------------------------------------------------

ALL = [
    Challenge(level=1, id="loopback_lurker", tools=("ss", "netstat", "lsof"), threat="Loopback Lurker",
              task="A Loopback Lurker (process {pid}) listens on this machine, on 127.0.0.1 only.\n"
                   "On which port? Answer with: answer <port>",
              help="Here, find how to list the ports programs listen on, with the process behind each.",
              hints=["ss lists sockets: -t TCP, -l listening, -n numbers, -p the program and its PID. "
                     "127.0.0.1 means only this machine can connect.",
                     "Try: ss -tlnp | grep 'pid={pid},'"],
              setup=lurker_setup, cleanup=stop, requires=["ss"], works=loopback_works, **NET),
    Challenge(level=1, id="address_adder", tools=("ip", "ifconfig"), threat="Address Adder",
              task="The Address Adder counts on you not knowing your own address.\n"
                   "What is this machine's IPv4 address on {dev}? Answer with: answer <address>",
              help="Here, find how to show the addresses of each network interface.",
              hints=["ip -br addr prints one line per interface: its name, UP or DOWN, and its addresses "
                     "(the /24 after an address is its prefix, not part of the address).",
                     "Try: ip -br addr show {dev}"],
              setup=adder_setup, verify=lambda w, m, v: v.strip().split("/")[0] in m["addrs"],
              requires=["ip"], works=gateway_works, **NET),
    Challenge(level=1, id="subnet_sprite", tools=("python3", "python", "ipcalc", "sipcalc"), threat="Subnet Sprite",
              task="The Subnet Sprite mixed addresses into hosts.txt.\n"
                   "How many of them are inside {net}? Answer with: answer <number>",
              hints=["{net} is a /22: 1,024 addresses, four /24 blocks in a row. Near misses just outside "
                     "are the trap. Python's ipaddress module knows the exact limits: bashou explain network cidr",
                     "Try: python3 -c \"import ipaddress as i; n = i.ip_network('{net}'); "
                     "print(sum(i.ip_address(l.strip()) in n for l in open('hosts.txt')))\""],
              setup=sprite_setup, requires=["python3"], **NET),
    Challenge(level=2, id="route_raven", tools=("ip",), threat="Route Raven",
              task="The Route Raven asks: a packet for {target} leaves this machine through a gateway.\n"
                   "What is the gateway's address? Answer with: answer <address>",
              hints=["ip route get asks the kernel which route an address would take, without sending anything: "
                     "the word after via is the gateway.",
                     "Try: ip route get {target}"],
              setup=raven_setup, requires=["ip"], works=gateway_works, after=("address_adder",), **NET),
    Challenge(level=2, id="resolver_rook", tools=("getent",), threat="Resolver Rook",
              task="The Resolver Rook asks what programs get for this machine's own name, {name}.\n"
                   "dig only asks DNS; programs read /etc/hosts first. Which address? Answer with: answer <address>",
              hints=["getent hosts asks the way programs do, following /etc/nsswitch.conf: /etc/hosts first, then "
                     "DNS. Any address it prints for the name is right.",
                     "Try: getent hosts {name}"],
              setup=rook_setup, verify=lambda w, m, v: v.strip() in m["addrs"], requires=["getent"], **NET),
    Challenge(level=2, id="six_serpent", tools=("python3", "python"), threat="Six Serpent",
              task="The Six Serpent wrote one IPv6 address twice in addrs.txt: once short, once in full.\n"
                   "Which address? Answer in its shortest form: answer <address>",
              hints=["The same IPv6 address can be written many ways: leading zeros dropped, one run of zero "
                     "groups as ::. Python's ipaddress writes every one in the shortest form, then compare.",
                     "Try: python3 -c \"import ipaddress as i; [print(i.ip_address(l.strip())) for l in open('addrs.txt')]\" "
                     "| sort | uniq -d"],
              setup=serpent_setup, requires=["python3"], after=("subnet_sprite",), **NET),
    Challenge(level=2, id="handshake_heron", threat="Handshake Heron",
              task="The Handshake Heron swallowed a connection in capture.pcap: one client sent SYN, "
                   "again and again, and never got an answer.\nWhich client port? Answer with: answer <port>",
              help="Here, find how to read a capture file instead of listening on the network.",
              hints=["tcpdump -nr capture.pcap reads the file (no root needed). Flags: [S] SYN, [S.] SYN-ACK, "
                     "[.] ACK. A filter keeps only some packets: 'tcp[tcpflags] == tcp-syn'.",
                     "Try: tcpdump -nr capture.pcap 'tcp[tcpflags] == tcp-syn' | awk '{{print $3}}' | sort | uniq -c"],
              setup=heron_setup, verify=port_answer, **TCPDUMP, **NET),
    Challenge(level=2, id="refused_revenant", threat="Refused Revenant",
              task="The Refused Revenant knocked on six ports in capture.pcap. One refused at once (RST), "
                   "one never answered, the others opened.\nWhich server port refused? Answer with: answer <port>",
              hints=["A refused connection is a SYN answered by a RST: tcpdump shows [R.]. Silence is different: "
                     "that's a firewall dropping, or a machine that's down.",
                     "Try: tcpdump -nr capture.pcap 'tcp[tcpflags] & tcp-rst != 0'"],
              setup=revenant_setup, verify=port_answer, after=("handshake_heron",), **TCPDUMP, **NET),
    Challenge(level=3, id="nxdomain_nixie", threat="NXDomain Nixie",
              task="The NXDomain Nixie hides in dns.pcap. One name doesn't exist (NXDOMAIN), another one "
                   "failed (SERVFAIL).\nWhich name doesn't exist? Answer with: answer <name>",
              hints=["Each DNS query and its answer share an id number: tcpdump prints it first, with + after a "
                     "query. Find the NXDomain answer's id, then the query with that id.",
                     "Try: id=$(tcpdump -nr dns.pcap 2>/dev/null | awk '/NXDomain/ {{print $6}}'); "
                     "tcpdump -nr dns.pcap 2>/dev/null | grep \" $id+ \""],
              setup=dns_setup, verify=same_name, after=("refused_revenant",), **TCPDUMP, **NET),
    Challenge(level=3, id="established_ettin", tools=("ss", "netstat"), threat="Established Ettin",
              task="The Established Ettin holds connections open to 127.0.0.1:{port}.\n"
                   "How many clients are connected to that port? Answer with: answer <number>",
              hints=["ss shows both ends of each connection on this machine: the clients' side has the port on "
                     "the right (Peer). ss filters by state and port: state established '( dport = :{port} )'.",
                     "Try: ss -tnH state established '( dport = :{port} )' | wc -l"],
              setup=ettin_setup, cleanup=stop, requires=["ss"], works=loopback_works,
              after=("loopback_lurker",), **NET),
]


def chest_setup(work, rng):
    port, pid = serve(work, rng, "::1")
    return {"args": {"pid": pid}, "answer": port, "pid": pid}


def v6_loopback():
    return "00000000000000000000000000000001" in Path("/proc/net/if_inet6").read_text() \
        if Path("/proc/net/if_inet6").exists() else False


def trial():
    from .trials import trial as make
    chest = make("trial_ss_ipv6", 1, "A guard (process {pid}) listens on the IPv6 loopback, ::1, next to this chest. "
                 "On which port? Then: answer <port>",
                 ["ss -tln lists listening TCP sockets; -6 keeps only IPv6, -p shows the process. ::1 is this "
                  "machine, like 127.0.0.1.",
                  "Try: ss -6tlnp | grep 'pid={pid},'"],
                 chest_setup, lambda w, m, v: v.strip() == str(m["answer"]), requires=["ss"], teaches=["ss"])
    chest.cleanup, chest.works = stop, v6_loopback
    return chest


CHEST = trial()
