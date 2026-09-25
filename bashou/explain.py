"""`bashou explain <subject> <topic>`: a short offline note with an example, for the code and network fights."""

from .i18n import _

BOLD, DIM, CYAN, RESET = "\x1b[1m", "\x1b[2m", "\x1b[36m", "\x1b[0m"

# language -> topic -> (text, example)
NOTES = {
    "python": {
        "list": ("A list keeps items in order: xs[0] is the first, xs[-1] the last, len(xs) how many. "
                 "Don't add or remove items of a list while a for loop walks over it: build a new list instead.",
                 "seen = []\nfor h in hosts:\n    if h not in seen:\n        seen.append(h)"),
        "dict": ("A dict maps keys to values: d['web'] = 3. Reading a missing key with d[k] raises KeyError; "
                 "d.get(k, 0) gives 0 instead. collections.Counter counts things for you.",
                 "counts[level] = counts.get(level, 0) + 1"),
        "loop": ("for walks over a list or a range: for i in range(3) gives 0, 1, 2. "
                 "A while loop runs until its condition is false: something inside must change it, or it never ends.",
                 "i = 0\nwhile i < tries:\n    print(i)\n    i += 1"),
        "recursion": ("A recursive function calls itself on a smaller piece. It needs a case that stops "
                      "without calling itself, and it must use what the inner call returns.",
                      "def total(tree):\n    return sum(total(v) if isinstance(v, dict) else v for v in tree.values())"),
        "json": ("json.load(fh) turns a JSON file into dicts and lists; then follow the keys.",
                 "python3 -c \"import json; print(json.load(open('f.json'))['db']['port'])\""),
        "url": ("URLs hide characters as %XX codes: %2f is /, %2e is a dot. urllib.parse.unquote decodes them.",
                "python3 -c \"import urllib.parse; print(urllib.parse.unquote('%2e%2e%2fetc'))\""),
        "base64": ("base64 turns bytes into text. A JWT is three base64url parts joined by dots: header, "
                   "payload, signature. The payload is only encoded, anyone can read it. Add '==' so the "
                   "padding is never too short.",
                   "python3 -c \"import base64; print(base64.urlsafe_b64decode('eyJhIjoxfQ' + '=='))\""),
        "subprocess": ("subprocess.run(['cmd', arg]) runs a program with a list of arguments: no shell, so "
                       "; $( ) and | in the data stay plain text. os.system and shell=True pass it to a shell.",
                       "subprocess.run(['echo', 'checking', host], check=True)"),
    },
    "rust": {
        "mut": ("In Rust a variable can't change unless you say so: let x = 5 is fixed, let mut x = 5 "
                "can change. rustc stops at 'cannot assign twice to immutable variable' and suggests mut.",
                "let mut count = 0;\ncount += 1;"),
        "shadowing": ("A new let with the same name hides the old variable: that's shadowing. Unlike mut, "
                      "the new one can have another type, handy to turn text into a number.",
                      "let guess = \"  42  \";\nlet guess: u32 = guess.trim().parse().unwrap();"),
        "const": ("A const is fixed forever and known when the program is built. It always says its type; "
                  "the name is in capitals by habit.",
                  "const MAX_POINTS: u32 = 100_000;"),
        "integers": ("Integer types say their size: u8 holds 0 to 255, u32 up to about 4 billion, i32 can be "
                     "negative. In a debug build, going past the limit panics ('attempt to add with overflow'). "
                     "`as` converts between them.",
                     "let total: u32 = small as u32 + 300;"),
    },
    "c": {
        "malloc": ("malloc(n) gives you n bytes on the heap, or NULL. Every malloc needs exactly one free "
                   "once you're done, or the memory leaks.",
                   "char *p = malloc(len + 1);\nif (!p) return 1;\n/* use p */\nfree(p);"),
        "array": ("An array of n items goes from index 0 to n - 1. Reading index n is past the end: "
                  "undefined behavior. The usual loop is i < n, never i <= n.",
                  "for (int i = 0; i < n; i++)\n    total += values[i];"),
        "string": ("A C string is chars ending with '\\0'. strcpy copies without checking the size of the "
                   "target: a long input writes past the buffer. Allocate strlen + 1, or use snprintf.",
                   "char *copy = malloc(strlen(s) + 1);\nif (copy) strcpy(copy, s);"),
        "recursion": ("A recursive function calls itself on a smaller problem. Without a base case that "
                      "returns directly, it calls itself until the stack overflows.",
                      "long sum_to(long n)\n{\n    if (n <= 0)\n        return 0;\n    return n + sum_to(n - 1);\n}"),
        "link": ("gcc builds in steps; the last one, the linker, joins every file of the program. \"undefined "
                 "reference to `f'\" means f is called but no file given to gcc has its code: list every .c file, "
                 "and add libraries at the end (-lm for sqrt and friends).",
                 "gcc main.c stats.c -o report\ngcc area.c -o area -lm"),
        "warnings": ("gcc -Wall turns on the warnings for the usual mistakes, -Wextra a few more. A warning doesn't "
                     "stop the build, but it's often a real bug: if (x = 5) stores 5 instead of comparing.",
                     "gcc -Wall -Wextra -g prog.c -o prog"),
        "gdb": ("gdb runs your program and lets you stop it and look inside. Build with -g for line numbers. "
                "run starts it; after a crash, bt shows the calls; break f stops at f; next goes one line; "
                "print x shows a variable; quit leaves.",
                "gcc -g prog.c -o prog\ngdb -q ./prog\n(gdb) break main\n(gdb) run\n(gdb) next\n(gdb) print x\n(gdb) bt"),
        "asan": ("gcc -fsanitize=address -g builds a program that stops at the first memory error "
                 "(overflow, use after free, leak) and says which line did it.",
                 "gcc -Wall -g -fsanitize=address prog.c -o prog && ./prog"),
    },
    "network": {
        "cidr": ("An IPv4 address is 32 bits. The /N after it says how many of those bits name the network; "
                 "the rest numbers the machines. Each bit less doubles the size: a /24 holds 256 addresses, "
                 "a /22 four times more. Python's ipaddress module does the math for you.",
                 "python3 -c \"import ipaddress; n = ipaddress.ip_network('10.4.0.0/22'); print(n[0], n[-1], n.num_addresses)\"\n"
                 "python3 -c \"import ipaddress; print(ipaddress.ip_address('10.4.2.7') in ipaddress.ip_network('10.4.0.0/22'))\""),
        "ipv6": ("An IPv6 address is 128 bits in 8 groups. Leading zeros in a group can go, and one run of "
                 "zero groups becomes ::. ::1 is the loopback, fe80:: addresses work only on their own link, "
                 "and a global address (often starting with 2) is reachable from other networks.",
                 "ip -6 addr\npython3 -c \"import ipaddress; print(ipaddress.ip_address('2001:db8::1').exploded)\""),
        "dns": ("Programs ask the C library for a name: it reads /etc/hosts first, then asks a DNS resolver. "
                "getent hosts shows what programs really get; dig asks DNS only. NXDOMAIN means the name "
                "doesn't exist; SERVFAIL means the lookup broke on the way.",
                "getent hosts example.org\ndig +short example.org\ndig AAAA example.org\nresolvectl status"),
        "tcp": ("A TCP connection opens with SYN, SYN-ACK, ACK. ss shows the sockets: LISTEN is a server "
                "waiting, ESTAB an open connection. 'Connection refused' comes back at once (nothing listens); "
                "'timed out' means no answer at all, often a firewall.",
                "ss -tlnp\nss -tn state established\nnc -zv localhost 22"),
    },
}


def main(args):
    if len(args) != 2 or args[0] not in NOTES or args[1] not in NOTES[args[0]]:
        print(_("Usage: bashou explain <subject> <topic>"))
        for lang, topics in NOTES.items():
            print(f"  {BOLD}{lang}{RESET}: {' '.join(topics)}")
        return 1
    text, example = NOTES[args[0]][args[1]]
    print(f"  {BOLD}{args[0]} {args[1]}{RESET}\n  {_(text)}\n")
    print("\n".join(f"    {CYAN}{line}{RESET}" for line in example.split("\n")))
    return 0
