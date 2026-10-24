# Certificates style: TLS, X.509 and openssl

Bashou teaches certificates (lessons `certs`, `certs_tools`, `certs_admin`, `certs_ca`, `certs_cnf`,
`certs_revoke`, skill `network`): what a
certificate says, how to read one with `openssl`, and how to run them on a server. Many people "fix"
certificate errors by turning the check off, so every sample here has to teach the real fix.

This file is the checklist for every certificate sample: lesson pages, adventure questions, fight
tasks, hints and the files fights make. The `certs-judge` agent (`.claude/agents/certs-judge.md`)
applies it after each change, and `tests/test_certs.py` checks the fights and the text. The bash in
these samples also follows [bash-style.md](bash-style.md).

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (to show the mistake) is
marked ✘ and followed by the right form. In a question, wrong choices may be wrong on purpose, but the
right answer and its explanation must follow the rules.

Facts are checked by running them (`openssl` 3 here, LibreSSL on a Mac) or against the source in the
table. Lifetimes and limits change: the CA/Browser Forum rules are checked again at writing time.

## Rules

| Id | Rule | Why | Source |
|---|---|---|---|
| T1 | Never teach `curl -k`, `--insecure`, `verify=False`, `-noverify` or `NODE_TLS_REJECT_UNAUTHORIZED=0` as a fix. They appear only as the ✘ example, followed by the real fix (trust the right CA with `--cacert`, fix the name or the chain). | Turning the check off accepts every attacker's certificate too, and stays in the script forever. | [RFC 9525 §6](https://www.rfc-editor.org/rfc/rfc9525#section-6), [curl `--insecure`](https://curl.se/docs/manpage.html#-k) |
| T2 | The names a certificate covers are in its Subject Alternative Name (SAN). Never say the CN is what clients check. A CSR or test cert in a sample always has a SAN. | Clients match the SAN only; browsers ignore the CN. | [RFC 9525 §6.3](https://www.rfc-editor.org/rfc/rfc9525#section-6.3), [CA/B BR 7.1.2.7](https://cabforum.org/working-groups/server/baseline-requirements/requirements/) |
| T3 | A server sends its certificate first, then the intermediates, in order, and not the root. In files: `fullchain.pem` = leaf then intermediates. | Clients build the path from what the server sends; the root is in their trust store already. | [RFC 8446 §4.4.2](https://www.rfc-editor.org/rfc/rfc8446#section-4.4.2), [Let's Encrypt chain](https://letsencrypt.org/certificates/) |
| T4 | Trust is the client's trust store: the system one, or a CA file given on purpose (`--cacert`, `-CAfile`). A private CA goes into the store the system's way: Debian `/usr/local/share/ca-certificates/*.crt` + `update-ca-certificates`, Rocky `/etc/pki/ca-trust/source/anchors/` + `update-ca-trust`. | Copying a cert anywhere else does nothing, and each family has its own tool. | [update-ca-certificates(8)](https://manpages.debian.org/bookworm/ca-certificates/update-ca-certificates.8.en.html), [RHEL shared certificates](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/securing_networks/using-shared-system-certificates_securing-networks) |
| T5 | Private keys: mode 600 (or 640 with a service group), owned by root or the service, never in git, never sent with the certificate. A sample that makes a key sets its mode. | Whoever has the key is the server. | [NIST SP 800-57 / 800-52r2](https://csrc.nist.gov/pubs/sp/800/52/r2/final) |
| T6 | Keys are RSA 2048 bits or more, or ECDSA P-256 / P-384. Signatures SHA-256 or better: never MD5 or SHA-1. | Shorter keys and these hashes are refused by clients and CAs. | [CA/B BR 6.1.5, 7.1.3](https://cabforum.org/working-groups/server/baseline-requirements/requirements/), [NIST SP 800-52r2](https://csrc.nist.gov/pubs/sp/800/52/r2/final) |
| T7 | Expiry is checked by a program, not a calendar: `openssl x509 -checkend SECONDS` (status 0 = still valid then), renewal by a timer (certbot's). Lifetimes are short and getting shorter: public certs at most 200 days since 2026-03-15, 100 from 2027-03-15, 47 from 2029-03-15. | A forgotten renewal is the most common certificate outage. | [CA/B ballot SC-081](https://cabforum.org/2025/04/11/ballot-sc081v3-introduce-schedule-of-reducing-validity-and-data-reuse-periods/), [certbot](https://eff-certbot.readthedocs.io/en/stable/using.html#automated-renewals) |
| T8 | TLS 1.2 and 1.3 only. A sample that sets versions or ciphers never turns on SSLv3, TLS 1.0 or 1.1. | Old versions have known attacks and are refused by current clients. | [RFC 8996](https://www.rfc-editor.org/rfc/rfc8996), [Mozilla Server Side TLS](https://wiki.mozilla.org/Security/Server_Side_TLS) |
| T9 | A self-signed certificate is for a lab or a test. For a private network, a private CA that clients trust (T4); for the internet, a public CA (Let's Encrypt). | A self-signed cert trains users to click through warnings. | [Let's Encrypt docs](https://letsencrypt.org/docs/) |
| T10 | `openssl s_client` gets `-servername HOST` (SNI) and, to check the name, `-verify_hostname HOST`. Its "Verify return code: 0 (ok)" is what tells the chain is good; the connection opening proves nothing. | Without SNI, a server with many sites may send another site's certificate; s_client connects even when the check fails. | [openssl-s_client(1)](https://docs.openssl.org/3.0/man1/openssl-s_client/) |
| T11 | Commands say which tool when LibreSSL (macOS `/usr/bin/openssl`) differs from OpenSSL 3, and give the Mac line: LibreSSL has no `x509 -ext`, `x509 -checkhost`, `s_client -verify_hostname` or `-noenc` (use `-text` and read the SAN, `-nodes`); `req -addext` needs LibreSSL 3.1.3+. Or `brew install openssl@3`. | Mac players run LibreSSL by default. | [LibreSSL openssl(1)](https://man.openbsd.org/openssl.1), [openssl-req(1)](https://docs.openssl.org/3.0/man1/openssl-req/) |
| T12 | `openssl x509` reading samples use `-noout` and the fields wanted (`-subject -issuer -dates -ext subjectAltName`), not a full `-text` dump, unless the page is about the dump. | Beginners drown in `-text`; the fields are what you check. | [openssl-x509(1)](https://docs.openssl.org/3.0/man1/openssl-x509/) |
| T13 | Passwords and keys never go on the command line in samples (`-passout pass:secret`): a lab key is made with `-noenc` (`-nodes` before OpenSSL 3), or the password comes from a file or the prompt. | argv is visible to every user in `ps`. | [openssl-passphrase-options(1)](https://docs.openssl.org/3.0/man1/openssl-passphrase-options/) |
| T14 | A CA certificate has `basicConstraints = critical, CA:TRUE` and `keyUsage = critical, keyCertSign, cRLSign`; a server's has `CA:FALSE` and `digitalSignature` (+ `extendedKeyUsage serverAuth`). `pathlen:N` is how many CAs may come below; server certificates don't count. An intermediate made for someone else gets a `pathlen`. | Clients refuse a signer without CA:TRUE or keyCertSign (errors 79, 32) and a chain deeper than a pathlen allows (error 25). | [RFC 5280 §4.2.1.9, §4.2.1.3](https://www.rfc-editor.org/rfc/rfc5280#section-4.2.1.9) |
| T15 | Revocation as it is now: CRLs are required of public CAs and OCSP optional since 2024-03-15; Let's Encrypt turned OCSP off in August 2025; browsers keep their own revocation lists (Firefox CRLite since 137). Never teach OCSP Must-Staple as current practice. Revoking replaces nothing: a new key and certificate follow. | Old guides still say "check OCSP"; the web moved to CRLs and short lifetimes. | [CA/B ballot SC-063](https://cabforum.org/2023/07/14/ballot-sc063v4-make-ocsp-optional-require-crls-and-incentivize-automation), [Let's Encrypt: ending OCSP](https://letsencrypt.org/2024/12/05/ending-ocsp/), [Mozilla CRLite](https://hacks.mozilla.org/2025/08/crlite-fast-private-and-comprehensive-certificate-revocation-checking-in-firefox/) |
| T16 | `openssl ca` samples set `basicConstraints` in the signing section and use `copy_extensions = copy` (adds only what the section doesn't set), never `copyall` (the request wins, CA:TRUE included). `serial` and `crlnumber` are hex. | A careless CA config lets any request become a CA. | [openssl-ca(1)](https://docs.openssl.org/3.0/man1/openssl-ca/) |
| T17 | Where openssl.cnf is comes from `openssl version -d` (OPENSSLDIR): Debian `/usr/lib/ssl` (links to `/etc/ssl/openssl.cnf`), Rocky `/etc/pki/tls` (includes the crypto policy), macOS LibreSSL `/etc/ssl`, Homebrew `$(brew --prefix)/etc/openssl@3`. Never a single path for everyone. | Each system and each openssl build has its own. | [openssl-version(1)](https://docs.openssl.org/3.0/man1/openssl-version/), [openssl-config(5)](https://docs.openssl.org/3.0/man5/config/) |

## Fights

- Offline only: every certificate, CA and key is made by the fight's setup, in the arena. A server is
  `openssl s_server` or Python's `http.server` with `ssl`, on 127.0.0.1, TLS 1.2+ (T8), Linux-only like the
  Loopback Lurker, stopped at cleanup.
- Setup makes lab keys and certificates with `openssl` commands only (no Python crypto library), with no passphrase (T9, T13).
- The verify reads files and runs `openssl` on them; it never trusts what the player typed alone when
  a file can prove it.
