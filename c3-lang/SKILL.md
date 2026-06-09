---
name: c3-lang
description: C3 language, writing, debugging, or reviewing .c3 files; c3c builds; C3 syntax, stdlib, and tooling
---

# C3 Programming Language

C3 is a systems language — an evolution over C with modules, optionals, slices, defer, generics, and compile-time features. Compiler: `c3c` (LLVM backend). **Baseline: 0.8.0.** Naming conventions (PascalCase types, snake_case functions) are enforced by the lexer.

Resources: [c3-lang.org](https://c3-lang.org) · [github.com/c3lang/c3c](https://github.com/c3lang/c3c) · [Discord](https://discord.gg/qN76R87)

**Docs:** [Language Fundamentals](https://c3-lang.org/language-fundamentals/variables/) · [Optionals (Essential)](https://c3-lang.org/language-common/optionals-essential/) · [Optionals (Advanced)](https://c3-lang.org/language-common/optionals-advanced/) · [Generics & Macros](https://c3-lang.org/generic-programming/generics/) · [Misc Advanced](https://c3-lang.org/misc-advanced/asm/) · [Stdlib source](https://github.com/c3lang/c3c/tree/v0.8.0/lib/std)

**Reference files (load on demand):**
- `references/stdlib.md` — full stdlib API (io, collections, math, threads, encoding, …)
- `references/advanced.md` — macros, generics, interfaces, operator overloading, contracts
- `references/c_interop.md` — calling C, exporting C-callable symbols
- `references/debugging-with-lldb.md` — how to debug C3 programs with LLDB: breakpoints, stepping, variables

---

## Syntax Cheatsheet

```c3
module myapp::utils;          // required for projects
import std::io;               // recursive by default

int x = 42;
const int MAX = 100;
int[] arr = { 1, 2, 3 };      // slice
int[4] fixed = { 1, 2, 3, 4 }; // fixed array (size left of name)

typedef MyInt = int;          // distinct type, no implicit conversion
typedef MyId @constinit = int; // also accepts literals
alias MyPtr = int*;           // transparent alias

fn int add(int a, int b) { return a + b; }
fn int square(int x) => x * x;            // short body
add(a: 1, b: 2);                          // named args

// Method: &self = pointer receiver
fn void Point.translate(&self, int dx, int dy) { self.x += dx; self.y += dy; }

struct Point { int x; int y; }
enum Status : uint { IDLE, BUSY, DONE }   // prefix inferred in context
bitstruct Flags : short { bool read_only : 0; bool hidden : 1; int priority : 2..4; }

Point p = { .x = 1, .y = 2 };
```

### Control Flow
```c3
// switch — NO implicit fallthrough; empty case falls to next non-empty case
switch (s) { case IDLE: case BUSY: io::printn("Not done"); case DONE: io::printn("Done"); }
switch (c) { case 'a': nextcase 'A'; case 'A': io::printn("A or a"); }  // explicit fallthrough

foreach (value : arr) { ... }
foreach (index, value : arr) { ... }
foreach (&value : arr) { *value *= 2; }   // by reference
foreach_r (value : arr) { ... }           // reverse
```

### Pointers, Slices
```c3
int* ptr = &value;

int[] s  = arr[1..3];  // inclusive end → indices 1,2,3
int[] s2 = arr[1:3];   // start:length
int[] s3 = arr[..];
int last = arr[^1];    // reverse index
sz len = s.len;

int[4] fixed;
takes_ptr(&fixed);     // fixed arrays don't decay — use & explicitly

String hello = "world";
char* cstr = hello.ptr;
```

---

## Error Handling (Optionals)

`T?` = value or fault. Zero overhead. Optionals can't be function parameters — use `Maybe{T}` to store them in structs.

```c3
faultdef FILE_NOT_FOUND, PERMISSION_DENIED;

fn String? read_file(String path) {
    if (!file::exists(path)) return FILE_NOT_FOUND~;  // ~ converts fault → empty optional
    return file::load_temp(path)!;                     // ! re-throws
}

String? r = read_file("a.txt");
if (catch err = r) { ... }             // catch + inspect fault
String s = read_file("b.txt")!;        // rethrow to caller
String t = read_file("c.txt") ?? "x"; // or-else (binds tighter than arithmetic)
String u = read_file("d.txt")!!;       // force unwrap — panic if empty
if (try s = read_file("e.txt") && try t = read_file("f.txt")) { ... }
```

| Op | Meaning |
|----|---------|
| `~` | fault → empty optional |
| `!` | rethrow to caller |
| `??` | or-else |
| `!!` | force unwrap (panic) |
| `if (catch err = x)` | inspect fault value |
| `if (try val = x)` | unwrap on success |

---

## Memory

```c3
// Heap
int* arr = mem::new_array(int, n);   // zero-initialized
mem::free(arr);

// Temp allocator — freed at @pool() exit; never return temp data past the scope
@pool() {
    String s = string::tformat("hello %s", name);
};

// defer — runs on any exit (return, break, fault)
fn void? process(String path) {
    File f = file::open(path, "r")!;
    defer f.close();
    defer try io::printn("ok");       // only on normal exit
    defer catch io::printn("failed"); // only on fault
}

// ZII: structs zero-init by default; @mustinit forbids it
struct Config @mustinit { String path; int retries; }
```

Key allocators: `mem::new(T)` / `mem::tnew(T)`, `mem::new_array(T,n)` / `mem::temp_array(T,n)`, `@clone(v)` / `@tclone(v)`, `mem::free(p)`.

---

## Modules

```c3
module myapp::net::http;

fn void pub_fn()  @public {}   // default
fn void priv_fn() @private {}  // module-only
fn void file_fn() @local {}    // file-only, cannot be overridden

attrdef @Hot = @inline, @export;
```

**Imports are recursive** (`import mylib` includes `mylib::net`, etc). Use `@norecurse` to opt out.

**Asymmetry:** types don't need a module prefix when unambiguous; functions always do.

---

## Compile-Time

```c3
$if env::WIN32:  fn void init() { }  $else  fn void init() { }  $endif
fn void win_only() @if(env::WIN32) { }

char[] data = $embed("assets/shader.glsl");
```

Key builtins: `$Typeof(expr)`, `$defined(expr)`, `$assert(cond)`, `Type::size` / `::alignment` / `::kind`, `@sizeof(expr)`, `$reflect(field).name`, `$eval("name")`, `$expand("expr")`, `$feature(F)`.

See `references/advanced.md` for macros, generics, interfaces, and operator overloading.

---

## Build

```bash
c3c init myproject
c3c run                      # build & run debug
c3c build release
c3c compile-run file.c3      # quick snippet test
c3c test / c3c benchmark
c3c vendor-fetch
c3c docgen
```

`project.json` targets: `"type": "executable"`, `"safe": true/false`, `"opt": "O0"/"O3"`, `"strip-unused": true`.

Verify a snippet: `c3c compile-run snippet.c3`. Add `--use-stdlib=no` for stdlib-free examples. `c3fmt` formats files; copy `assets/.c3fmt` to project root first.

---

## Testing

```c3
fn void test_add() @test { assert(add(1, 2) == 3); }
fn void bench_add() @benchmark { for (int i = 0; i < 1000; i++) add(i, i+1); }
```

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| `char[64]` won't cast to `char*` | Fixed arrays don't decay — use `&array_name` |
| Function call fails without prefix | Functions always need `module::fn()` |
| Switch falls through unexpectedly | C3 auto-breaks; use `nextcase` for explicit fallthrough |
| `a & b == c` wrong result | Bitwise binds **tighter** than `==` in C3 (opposite of C) — parenthesize |
| `??` precedence surprise | `f() ?? x + 1` is `(f() ?? x) + 1` — binds tighter than arithmetic |
| Temp data dies after `@pool()` | Copy results out before the block closes |
| `#param` side effects repeat | `#expr` args re-evaluated on each use — not memoized |
| Dangling slice | Slice lifetime tied to underlying pointer — don't return stack/temp slices |
| Unhandled optional | `String s = fn_returning_optional()` — missing `!`, `??`, or `catch` |
| Enum as bitmask | Use `bitstruct` instead |
| Enum arithmetic | Use `.ordinal` for math; `++`/`--` wrap around |
| Implicit narrowing / float→int | Explicit cast required |
