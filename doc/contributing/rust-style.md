# Rust style: one file with rustc, a project with cargo

Bashou teaches Rust two ways, and every piece of Rust we show belongs to one of them:

- **One file with rustc** (`rustc counter.rs && ./counter`): what the fights use. No project, one
  `main`, built in debug mode. Fine to learn one idea at a time.
- **A project with cargo** (`cargo new`, `cargo run`): how Rust is written for real. Dependencies,
  tests, `--release` builds, `cargo fmt` and `cargo clippy`.

This file is the checklist for every Rust sample in Bashou: lesson pages (`rust_*`), the rust
adventure questions, the Rust fights of `bashou/challenges/rust.py`, their hints and starter files.
The `rust-judge` agent (`.claude/agents/rust-judge.md`) applies it after each change, and
`tests/test_rust_style.py` builds every file a fight writes.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (the bug a fight asks to
fix, a wrong choice) is marked ✘ and followed by the right form. The right answer, its explanation,
the hints and the fixed file must follow the rules.

Facts are checked by compiling (`rustc`, and the oldest version in the table when the claim depends
on it) or against the official docs (the Book, the Reference, the rustc and cargo books, the error
index), never from memory.

## Both ways

| Id | Rule | Why | Source |
|---|---|---|---|
| R1 | Every full sample builds (or fails with exactly the error the text says) with the edition the player's command uses. `rustc file.rs` builds in edition 2015, rustc's default; verify builds with `--edition 2021`: a file must give the same result with both. | A player who types the shown command must see what we promise. | [rustc --edition](https://doc.rust-lang.org/rustc/command-line-arguments.html#--edition-specify-the-edition-to-use), [edition guide](https://doc.rust-lang.org/edition-guide/) |
| R2 | A rustc error is quoted with its code and its exact words (`error[E0382]: borrow of moved value: `a``), checked by compiling, on the oldest and the newest rustc when the words could have changed. | The player searches the words they see; the code leads to the error index. | [error index](https://doc.rust-lang.org/error_codes/error-index.html) |
| R3 | Overflow is said with its build: a debug build panics, a release build (`-O`, `--release`) wraps. For an intended wrap or check: `wrapping_add`, `checked_add`, `saturating_add`. | "Rust never overflows" and "Rust always panics" are both false. | [Book 3.2, integer overflow](https://doc.rust-lang.org/book/ch03-02-data-types.html#integer-overflow) |
| R4 | `as` between integers is taught for widening (`u8 as u32`). Narrowing with `as` truncates silently: say so, and show `u8::try_from(x)` for a checked conversion. | `300 as u8` is 44, no error. | [Reference, numeric cast](https://doc.rust-lang.org/reference/expressions/operator-expr.html#numeric-cast), [TryFrom](https://doc.rust-lang.org/std/convert/trait.TryFrom.html) |
| R5 | Ownership words are the Book's: owner, move, borrow, reference, `&`, `&mut`, drop, Copy, clone. A move is not a copy of the heap data; `clone()` is, and costs memory. | Players read the Book next; other words confuse. | [Book 4.1](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) |
| R6 | The borrow rule: at any moment many `&` or one `&mut`. A borrow lasts until its last use, not until the end of the block. | Since non-lexical lifetimes (2018 edition, then 2015 in 1.36) the end of the block is wrong. | [Book 4.2](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html) |
| R7 | Never claim safe Rust can't leak memory. It prevents use-after-free, double free and data races; leaks stay possible (`Rc` cycles, `Box::leak`, `mem::forget` are safe). | The Book says so. | [Book 15.6](https://doc.rust-lang.org/book/ch15-06-reference-cycles.html), [mem::forget](https://doc.rust-lang.org/std/mem/fn.forget.html) |
| R8 | A function that only reads text takes `&str`, a list `&[T]`: not `&String` or `&Vec<T>`. A function takes `String` only when it keeps it. | `&str` accepts both `&String` and `"literals"`; Clippy flags `&String`. | [Book 4.3](https://doc.rust-lang.org/book/ch04-03-slices.html#string-slices-as-parameters), [clippy ptr_arg](https://rust-lang.github.io/rust-clippy/master/index.html#ptr_arg) |
| R9 | Expected failures (a missing file, bad input) return a `Result` and are handled or passed up with `?`. `panic!`, `unwrap()` are for bugs; when a fixed file uses `unwrap()` or `expect()`, the text says it stops the program, and `expect("why")` is preferred. | "To panic or not to panic" in the Book. | [Book 9.3](https://doc.rust-lang.org/book/ch09-03-to-panic-or-not-to-panic.html), [Book 9.2, ?](https://doc.rust-lang.org/book/ch09-02-recoverable-errors-with-result.html#a-shortcut-for-propagating-errors-the--operator) |
| R10 | Names: `snake_case` for variables and functions, `CamelCase` for types, `SCREAMING_SNAKE_CASE` for `const` and `static`. Code laid out the way `rustfmt` does (4 spaces). | rustc warns on other names; every Rust project runs rustfmt. | [API guidelines, naming](https://rust-lang.github.io/api-guidelines/naming.html), [style guide](https://doc.rust-lang.org/style-guide/) |
| R11 | A fixed file (and a right answer's code) builds with no warning. | A warning left in teaches to ignore warnings. | [rustc lints](https://doc.rust-lang.org/rustc/lints/index.html) |
| R12 | A feature newer than the oldest rustc in the table says what it needs ("needs Rust 1.65+"): `let … else` (1.65), `std::io::IsTerminal` (1.70), `LazyLock` (1.80)… | Debian 12 players have rustc 1.63. | [releases](https://github.com/rust-lang/rust/blob/master/RELEASES.md), [Debian rustc](https://packages.debian.org/search?keywords=rustc) |

## One file with rustc

Fine for a fight. When a lesson shows it, it says once that real projects use cargo.

| Id | Allowed with rustc | In a cargo project instead | Source |
|---|---|---|---|
| RC1 | `rustc file.rs && ./file`, a debug build | `cargo run`; `cargo build --release` for speed | [Book 1.2](https://doc.rust-lang.org/book/ch01-02-hello-world.html), [Book 1.3](https://doc.rust-lang.org/book/ch01-03-hello-cargo.html) |
| RC2 | No dependencies: only `std` | crates in `Cargo.toml`, `Cargo.lock` committed for a program | [cargo FAQ, Cargo.lock](https://doc.rust-lang.org/cargo/faq.html#why-have-cargolock-in-version-control) |
| RC3 | Check by running it | `cargo test`, `cargo clippy`, `cargo fmt` | [Book 11](https://doc.rust-lang.org/book/ch11-01-writing-tests.html), [clippy](https://doc.rust-lang.org/clippy/) |

## Versions players run

| Where | rustc | Note |
|---|---|---|
| Debian 12 (apt) | 1.63 | the oldest we support: no `let … else` |
| Debian 13 (apt) | 1.85 | edition 2024 is 1.85+ |
| Rocky 9 (AppStream `rust`) | recent, updated in minor releases | check `rustc --version` |
| rustup (Mac and most learners) | latest stable | |
