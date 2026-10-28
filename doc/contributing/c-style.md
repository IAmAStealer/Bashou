# C style: a file you build, a program you debug

Bashou teaches C to show how a computer runs a program: compile, link, stack and heap, pointers,
gdb. Every C sample is a small file built by hand with `gcc`, and two things matter more than in
other languages: what the standard promises (and what it leaves undefined), and what differs between
Linux and macOS, where `gcc` is Apple's clang.

This file is the checklist for every C sample in Bashou: lesson pages (`compilation`, `gcc_use`,
`stack_heap`, `pointers`, `debugger`), the c adventure questions, the C fights of
`bashou/challenges/code.py` and `debug.py`, their hints and starter files. The `c-judge` agent
(`.claude/agents/c-judge.md`) applies it after each change, and `tests/test_c_style.py` builds every
file a fight writes with `gcc -std=c99 -pedantic -Wall -Wextra`.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (the bug a fight asks to
fix, a wrong choice) is marked ✘ and followed by the right form. The right answer, its explanation,
the hints and the fixed file must follow the rules.

Facts are checked by building and running (gcc, and clang when the claim is about macOS) or against
the references (the C standard through cppreference, the GCC, GDB and Clang manuals, SEI CERT C),
never from memory.

## The code

| Id | Rule | Why | Source |
|---|---|---|---|
| C1 | Samples are standard C99 and build with no warning under `-std=c99 -pedantic -Wall -Wextra` (the bug on purpose aside). No GNU extensions, no `void main`. | Players build with gcc 11 to 14 and Apple clang: only standard C behaves the same everywhere. | [GCC warning options](https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html), [cppreference: main](https://en.cppreference.com/w/c/language/main_function) |
| C2 | Undefined behavior is called that: reading past an array, signed overflow, use after free, an uninitialized read "may crash, print garbage or seem to work". Never "it always segfaults". | The compiler may do anything; a sample that seems to work teaches the wrong lesson. | [cppreference: undefined behavior](https://en.cppreference.com/w/c/language/behavior) |
| C3 | Every `malloc`/`calloc`/`realloc` result is checked for `NULL`, every block is freed once, and a freed pointer is not used again (set it to `NULL` when it lives on). Sizes are written `malloc(n * sizeof *p)`. | Leaks, double free and use after free are the bugs these lessons exist for. | [cppreference: malloc](https://en.cppreference.com/w/c/memory/malloc), [CERT MEM30-C](https://wiki.sei.cmu.edu/confluence/display/c/MEM30-C.+Do+not+access+freed+memory) |
| C4 | Text input and copies carry the buffer size: `fgets`, `snprintf`. Never `gets` (removed in C11), never `strcpy`/`sprintf`/`strcat` into a fixed buffer from input. `strncpy` doesn't always end the string with `\0`: say so if it appears. | Buffer overflows. | [cppreference: gets](https://en.cppreference.com/w/c/io/gets), [CERT STR31-C](https://wiki.sei.cmu.edu/confluence/display/c/STR31-C.+Guarantee+that+storage+for+strings+has+sufficient+space+for+character+data+and+the+null+terminator) |
| C5 | `int main(void)` or `int main(int argc, char *argv[])`. Errors go to `stderr` (`fprintf(stderr, …)`, `perror`) and the program returns non-zero (`EXIT_FAILURE`). | The shell and scripts read the exit code (bash-style). | [cppreference: perror](https://en.cppreference.com/w/c/io/perror), [cppreference: EXIT_FAILURE](https://en.cppreference.com/w/c/program/EXIT_status) |
| C6 | `printf` formats match the type: `%d` int, `%ld` long, `%zu` size_t, `%p` with `(void *)`. | A wrong format is undefined behavior; `-Wall` (`-Wformat`) catches most. | [cppreference: printf](https://en.cppreference.com/w/c/io/fprintf) |
| C7 | Sizes are not promised by C: `int` is at least 16 bits (32 on every platform players use), `long` is 64 bits on Linux and macOS but 32 on Windows. Exact sizes: `<stdint.h>` (`int32_t`, `uint8_t`). | "int is 4 bytes" is a platform fact, not a C fact. | [cppreference: arithmetic types](https://en.cppreference.com/w/c/language/arithmetic_types) |
| C8 | `sizeof arr / sizeof arr[0]` only on a real array in the same function; a parameter `int a[]` is a pointer, so the size travels as another parameter. | The classic wrong count. | [CERT ARR01-C](https://wiki.sei.cmu.edu/confluence/display/c/ARR01-C.+Do+not+apply+the+sizeof+operator+to+a+pointer+when+taking+the+size+of+an+array) |
| C9 | Stack and heap facts are said as platform facts: the stack's size (8 MB by default on most Linux, `ulimit -s`), its direction, the address layout. C itself only knows automatic and allocated storage. | A drawing of memory is a Linux picture, and must say so when it matters. | [getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html), [cppreference: storage duration](https://en.cppreference.com/w/c/language/storage_duration) |
| C10 | Names: `lower_case` for variables and functions, `UPPER_CASE` for macros; braces and 4-space indent the same in every sample. | One look for every file a player reads. | [GNU coding standards](https://www.gnu.org/prep/standards/html_node/Formatting.html), [Linux kernel style](https://www.kernel.org/doc/html/latest/process/coding-style.html) |

## Building and debugging

| Id | Rule | Why | Source |
|---|---|---|---|
| CD1 | Once warnings are taught, every build line shows `-Wall` (and `-Wextra` where it's shown); a debug build adds `-g` (and `-Og` or `-O0`); sanitizers are `-fsanitize=address,undefined`. | Warnings are the cheapest bug finder. | [GCC debugging options](https://gcc.gnu.org/onlinedocs/gcc/Debugging-Options.html), [GCC instrumentation](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html) |
| CD2 | A gcc message is quoted exactly as gcc 12+ prints it, checked by building. When the words differ on macOS (`gcc` there is clang: `Undefined symbols for architecture…` instead of `undefined reference to`), the text says so or uses words both share. | The Mac player sees clang's words. | [Clang diagnostics](https://clang.llvm.org/docs/DiagnosticsReference.html), [GCC link options](https://gcc.gnu.org/onlinedocs/gcc/Link-Options.html) |
| CD3 | Libraries go after the files that use them: `gcc area.c -o area -lm`. The `.h` is read by `#include`, never listed on the command line. | The linker reads left to right. | [GCC link options](https://gcc.gnu.org/onlinedocs/gcc/Link-Options.html) |
| CD4 | gdb commands are gdb's words (`run`, `bt`, `break`, `print`, `next`, `step`, `continue`), and the text says that on a Mac the debugger is `lldb` (same `bt`, `breakpoint set`), since gdb doesn't run on Apple Silicon. | A Mac player can't follow a gdb-only lesson. | [GDB manual](https://sourceware.org/gdb/current/onlinedocs/gdb.html/), [GDB to LLDB map](https://lldb.llvm.org/use/map.html) |
| CD5 | Valgrind is Linux only; on a Mac the memory checker is `-fsanitize=address`. | Valgrind doesn't support recent macOS. | [Valgrind](https://valgrind.org/info/platforms.html), [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html) |

## Versions players run

| Where | Compiler | Debugger |
|---|---|---|
| Debian 12 | gcc 12 | gdb 13 |
| Debian 13 | gcc 14 | gdb 16 |
| Rocky 9 | gcc 11 | gdb 10+ |
| macOS | Apple clang, also called `gcc` | lldb |
