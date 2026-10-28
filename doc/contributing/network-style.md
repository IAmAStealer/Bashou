# Network style: looking at your machine, talking to others

Bashou teaches networking from the terminal: addresses and routes (`ip`), ports (`ss`, `nc`), names
(`dig`, `getent`, `resolvectl`), the path (`ping`, `tracepath`), and what an error says (refused,
timed out, NXDOMAIN). Certificates have their own guide (`certs-style.md`).

This file is the checklist for every network sample in Bashou: the lessons `network`, `ip_addr`,
`ipv6`, `dns`, `dns_tools`, `tcp`, `net_debug` (and the network parts of `keys` and `pipeline`), the
network adventure questions, the fights of `bashou/challenges/network.py`, their hints and files.
The `network-judge` agent (`.claude/agents/network-judge.md`) applies it after each change, and
`tests/test_network_style.py` checks every address players read.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (a wrong choice, the
mistake a fight shows) is marked ✘ and followed by the right form. The right answer, its explanation
and the hints must follow the rules.

Facts are checked by running the command (here, on loopback or a scratch namespace, never against
someone else's machine) or against the man pages and RFCs, never from memory.

| Id | Rule | Why | Source |
|---|---|---|---|
| N1 | Addresses in samples are documentation addresses (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, `2001:db8::/32`), private ones (`10/8`, `172.16/12`, `192.168/16`, `fd00::/8`) or special ones (`127.0.0.1`, `::1`, `fe80::`). Names are `example.com`, `.org`, `.net`, or end in `.example`, `.test`, `.invalid` (RFC 2606), `.internal` for a private network (reserved by ICANN, 2024). Public resolvers (`1.1.1.1`, `9.9.9.9`, `8.8.8.8`) only as themselves. | A real address changes and belongs to someone; a player who copies it sends traffic there. | [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737), [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849), [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606), [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918), [ICANN: .internal](https://www.icann.org/en/board-activities-and-meetings/materials/approved-resolutions-special-meeting-of-the-icann-board-29-07-2024-en) |
| N2 | When the player is told to run a command against a real name (`dig example.org`), the text says their numbers will differ from the drawing. | The drawing shows documentation addresses (N1). | [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606#section-3) |
| N3 | Linux tools are iproute2's: `ip addr`, `ip route`, `ss`. `ifconfig`, `netstat`, `route` are named only as the old tools (net-tools isn't installed on new Debian and Rocky). On a Mac: `ifconfig`, `netstat -rn`, `lsof -i`. | A Debian 12 player has no `ifconfig`. | [ip(8)](https://man7.org/linux/man-pages/man8/ip.8.html), [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html), [netstat(8) note](https://man7.org/linux/man-pages/man8/netstat.8.html#NOTES) |
| N4 | Names: `getent hosts NAME` asks like programs do (with `/etc/hosts`); `dig` asks DNS only. On systemd-resolved, `/etc/resolv.conf` points at the stub `127.0.0.53`: the real servers are in `resolvectl status`. On a Mac: `dscacheutil -q host -a name NAME`, `scutil --dns`. | `dig` and the browser can disagree, and that is often the bug. | [getent(1)](https://man7.org/linux/man-pages/man1/getent.1.html), [systemd-resolved(8)](https://www.freedesktop.org/software/systemd/man/latest/systemd-resolved.service.html), [dig](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility) |
| N5 | Errors are told apart by what they mean: refused (the machine answered, nothing listens on that port), timed out (no answer: firewall, wrong route, machine down), NXDOMAIN (the name doesn't exist), SERVFAIL (the resolver failed). | Each one points to a different layer. | [connect(2)](https://man7.org/linux/man-pages/man2/connect.2.html), [RFC 9499](https://www.rfc-editor.org/rfc/rfc9499) |
| N6 | `ping` gets a count (`ping -c 3`): without it, ping runs until Ctrl-C (Linux and macOS). No answer to ping doesn't mean down: ICMP is often blocked. `tracepath` works without root (Rocky: in iputils; Debian: `apt install iputils-tracepath`); `traceroute` may need installing too. | Beginners wait forever, or conclude wrongly. | [ping(8)](https://man7.org/linux/man-pages/man8/ping.8.html), [tracepath(8)](https://man7.org/linux/man-pages/man8/tracepath.8.html) |
| N7 | DNS uses UDP and TCP (large answers, zone transfers); "UDP is unreliable" means no delivery guarantee, not that it often fails. | Half-truths in questions. | [RFC 7766](https://www.rfc-editor.org/rfc/rfc7766) |
| N8 | Listening on `127.0.0.1` is only reachable from the machine itself; `0.0.0.0` (or `::`) on every interface. Ports below 1024 need root on Linux. | The classic "works on my machine". | [ip(7)](https://man7.org/linux/man-pages/man7/ip.7.html), [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html) |
| N9 | CIDR and subnet arithmetic is checked with Python's `ipaddress` (or `ipcalc`), never done in your head. | Off-by-one in masks and ranges. | [ipaddress](https://docs.python.org/3/library/ipaddress.html) |
| N10 | SSH keys: `ssh-keygen -t ed25519`, a passphrase, `~/.ssh` 700 and the private key 600. A new host's fingerprint is checked, never skipped with `StrictHostKeyChecking=no`. | The key is the password; skipping the check invites a man in the middle. | [ssh-keygen(1)](https://man.openbsd.org/ssh-keygen), [ssh_config(5)](https://man.openbsd.org/ssh_config#StrictHostKeyChecking) |
| N11 | Firewalls are named per system: Rocky uses firewalld (`firewall-cmd`), Debian nftables (`nft`; installed, but no rules until `nftables.service` is enabled; ufw only if installed), macOS pf and the application firewall. A sample never opens a port without saying which. | One command doesn't fit all. | [firewalld](https://firewalld.org/documentation/), [nftables wiki](https://wiki.nftables.org/wiki-nftables/index.php/Main_Page), [Debian nftables](https://wiki.debian.org/nftables) |
| N12 | `curl` in scripts follows bash-style (fail on HTTP errors, a time limit) and certs-style (never `-k`). | Same habits everywhere. | [curl manual](https://curl.se/docs/manpage.html) |
