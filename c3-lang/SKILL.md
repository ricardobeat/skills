---
name: c3-lang
description: Use whenever C3 (the systems language by Christoffer Lernö) appears — writing, reading, debugging, porting, or reviewing `.c3` source; setting up `project.json` / `c3c` builds; explaining C3 syntax, modules, optionals, faults, defer, allocators, macros, or stdlib APIs. Trigger even when the user only mentions `c3c`, "C3 lang", a `.c3` filename, or pastes code with `module`, `fn`, `faultdef`, or `?`-suffixed types. Covers C3 **0.8.0** and migration from 0.7.x.
---

# C3 Programming Language

## Overview

C3 is a systems programming language — "an evolution, not a revolution" over C. It keeps C's mental model and ABI compatibility while adding modules, optionals, slices, defer, generics, and compile-time features. Compiler: `c3c` (LLVM backend). Current version: **0.8.0** (2026-05-12).

**Core principles:** Procedural, minimalist, data is inert, zero-is-initialization (ZII — zero value is always valid), no GC, no borrow checker, seamless C interop.

Resources: [c3-lang.org](https://c3-lang.org) · [github.com/c3lang/c3c](https://github.com/c3lang/c3c) · [Discord](https://discord.gg/qN76R87).

**Companion files (load on demand):**
- `references/stdlib.md` — full standard library API surface (io, collections, math, threads, encoding, …)
- `references/advanced.md` — macros, generics, interfaces, operator overloading, contracts
- `references/migration_0_7_to_0_8.md` — load when reading or updating pre-0.8 code
- `references/c_interop.md` — load when wrapping or calling C, or exporting C-callable symbols

---

## Syntax Cheatsheet

### Naming Conventions (enforced by grammar)
| Style | Used for |
|-------|----------|
| `UpperCamelCase` | Types, interfaces, faults |
| `snake_case` | Functions, variables, struct members |
| `ALL_CAPS` | Constants, enum values |
| `$lower` | Compile-time variables (macros only) |
| `#param` | Unevaluated expression parameters (macros) |

### Primitives
```c3
// Integers (fixed bit widths — not platform-dependent)
ichar  short  int  long  int128    // signed: 8, 16, 32, 64, 128 bits
char   ushort uint ulong uint128   // unsigned
iptr   uptr                        // pointer-sized signed/unsigned
sz                                 // size type (like size_t — 0.8.0 replaces usz/isz)

// Floats
float16  bfloat16  float  double  float128

// Other
bool  char  void  any  typeid
```

### Declarations
```c3
module myapp::utils;          // module declaration (required for projects)
import std::io;               // import (recursive by default)
import std::collections::list @norecurse;  // non-recursive import

int x = 42;                   // variable
const int MAX = 100;          // constant
int[] arr = { 1, 2, 3 };      // slice literal
int[4] fixed = { 1, 2, 3, 4 }; // fixed-size array (size left of name!)

typedef MyInt = int;          // distinct type (no implicit conversion; structlike by default in 0.8.0)
typedef MyId @constinit = int; // also accept literals: get_by_id(1)
alias  MyPtr = int*;          // transparent alias (like C typedef)
```

### Functions and Methods
```c3
fn int add(int a, int b) { return a + b; }

// Method: receiver type before dot, pointer receiver for mutation
fn void Point.translate(Point* self, int dx, int dy) {
    self.x += dx;
    self.y += dy;
}

// Receiver shorthand: `&self` expands to `Point* self`, `self` to `Point self`
fn int Point.dist_sq(&self)        { return self.x*self.x + self.y*self.y; }
fn Point Point.scaled(self, int k) { return { self.x*k, self.y*k }; }

// Named arguments
add(a: 1, b: 2);

// Variadic
fn void log(String fmt, args...) { io::printfn(fmt, ...args); }

// Short body (`=> expr`)
fn int square(int x) => x * x;
```

### Structs and Enums
```c3
struct Point { int x; int y; }  // no trailing semicolon

enum Status : uint { IDLE, BUSY, DONE }  // backed by uint (must have ≥1 value)

// Inside an expression of known enum type, the `Status::` prefix is inferred —
// you don't have to qualify each operand:
Status s = ok ? DONE : IDLE;     // both branches inferred as Status
if (s == BUSY) { ... }           // BUSY inferred as Status

// Enum with associated values
enum Shape {
    CIRCLE = { float radius },
    RECT   = { float w, h }
}
// Reflection: Shape.values, Shape.names, Shape.len, Shape.membersof.
// `++`/`--` step with wrap-around. `+`/`-` removed in 0.8.0 — use .ordinal.

// Bitstruct (replaces C bitfields — use this for bit flags, NOT an enum)
bitstruct Flags : short {
    bool read_only : 0;
    bool hidden    : 1;
    int  priority  : 2..4;
}

// Union
union IntOrFloat { int i; float f; }

// Struct initialization
Point p = { .x = 1, .y = 2 };
Point q = { 1, 2 };

// Struct literal in call
draw({ .x = 5, .y = 10 });
```

### Control Flow
```c3
// if / else
if (x > 0) { ... } else { ... }

// switch — NO implicit fallthrough; use nextcase for explicit
switch (status) {
    case IDLE:
    case BUSY:
        io::printn("Not done");     // empty case falls through to next
    case DONE:
        io::printn("Done");         // auto-breaks
    default:
        io::printn("Unknown");
}

// Expression switch (no subject)
switch {
    case x > 100: io::printn("big");
    case x > 10:  io::printn("medium");
    default:      io::printn("small");
}

// nextcase (explicit fallthrough)
switch (c) {
    case 'a': nextcase 'A';   // jump to case 'A'
    case 'A': io::printn("A or a");
}

// Loops
for (int i = 0; i < n; i++) { ... }
while (cond) { ... }
do { ... } while (cond);

foreach (value : arr) { ... }             // value
foreach (index, value : arr) { ... }      // index + value
foreach (&value : arr) { *value *= 2; }   // by reference (mutate in place)
foreach_r (value : arr) { ... }           // reverse

// break / continue with labels
outer: for (...) {
    inner: for (...) {
        break outer;
    }
}
```

### Pointers, Arrays, Slices
```c3
int value = 42;
int* ptr = &value;     // address-of
int deref = *ptr;      // dereference
*ptr = 100;            // write through pointer

// Slices (preferred over pointer+length)
int[] s  = arr[1..3];  // start..end — END IS INCLUSIVE → indices 1, 2, 3
int[] s2 = arr[1:3];   // start:length → 3 elements starting at index 1
int[] s3 = arr[..];    // whole slice
int[] s4 = arr[..4];   // from 0 through 4 (inclusive)
int[] s5 = arr[1..];   // from 1 to end
int last = arr[^1];    // ^n reverse-index: ^1 = len-1 (last element)
int[] tail = arr[^2..]; // last 2 elements
sz len = s.len;        // slice length

// Fixed array → pointer
int[4] fixed;
int* p = &fixed;       // get pointer to first element
fn void takes_ptr(int* p) { ... }
takes_ptr(&fixed);     // pass fixed array to C-style function

// String (= char[])
String hello = "world";
char* cstr = hello.ptr;  // get C pointer
```

---

## Error Handling (Optionals)

C3 uses Optional types: `T?` is either a `T` value or a **fault** (empty). Zero runtime overhead vs. exceptions.

```c3
// Define faults
faultdef FILE_NOT_FOUND, PERMISSION_DENIED;

// Function returning optional
fn String? read_file(String path) {
    if (!file::exists(path)) return FILE_NOT_FOUND~;  // ~ converts fault → empty optional
    return file::load_temp(path)!;  // ! re-throws any fault from load_temp
}

fn void main() {
    // Pattern 1: catch the fault
    String? result = read_file("data.txt");
    if (catch err = result) {
        switch (err) {
            case FILE_NOT_FOUND:  io::printn("Not found");
            default:              io::printfn("Error: %s", err);
        }
        return;
    }
    // result is unwrapped here — use as String
    io::printfn("Content: %s", result);

    // Pattern 2: rethrow with ! (propagates fault to caller)
    String content = read_file("cfg.txt")!;

    // Pattern 3: default value with ??  (binds tighter than + - in 0.8.0)
    String cfg = read_file("optional.cfg") ?? "default";

    // Pattern 4: force unwrap (panic if empty) !!
    String must = read_file("required.cfg")!!;

    // Pattern 5: if(try) happy-path check — chain with &&, || not allowed
    if (try s = read_file("maybe.txt") && try cfg2 = read_file("b.txt")) {
        io::printfn("Got: %s %s", s, cfg2);
    }
}
```

| Operator | Meaning |
|----------|---------|
| `~` | Convert fault value to empty optional |
| `!` | Rethrow: propagate fault to caller |
| `??` | Or-else: provide default if empty |
| `!!` | Force unwrap: panic if empty |
| `@catch(x)` | Get the fault value (not the result) |
| `@ok(x)` | `true` if value is present |

---

## Memory Management

Manual, with an ergonomic three-tier system. No GC, no borrow checker.

```c3
// Tier 1: Stack (default for local fixed-size)
int[1024] buf;

// Tier 2: Heap
int* arr = mem::new_array(int, n);    // zero-initialized
int* raw = mem::alloc_array(int, n);  // uninitialized (faster)
mem::free(arr);

// Tier 3: Temporary allocator (arena scoped to @pool block)
@pool() {
    int* temp = tmalloc(int::size * 100);     // 0.8.0: int::size, not int.sizeof
    String s = string::tformat("hello %s", name);
    DString ds;
    ds.tinit();
    // all allocations freed automatically on scope exit
};

// always_assert(cond) — fires even in unsafe/release mode (unlike plain assert).

// defer for cleanup (runs on any exit — return, break, error)
fn void? process(String path) {
    File f = file::open(path, "r")!;
    defer f.close();                          // always
    defer try io::printn("ok");               // only on normal exit
    defer catch io::printn("failed");         // only on fault exit
    defer (catch err) io::printfn("err=%s", err);  // bind the fault
    // ... f is closed even if we return early or fault
}
```

**Allocator naming:**
- `mem::new(T)` / `mem::tnew(T)` — heap / temp
- `mem::new_array(T, n)` / `mem::temp_array(T, n)` — heap / temp array
- `@clone(v)` / `@tclone(v)` — heap / temp clone
- `mem::free(p)` — deallocate
- `destroy(x)` — deallocate + close resources (files, etc.)

**ZII principle:** Design structs so the zero value is valid. Use `= {}` or just declare — it's zeroed. Add `@mustinit` to a type to forbid zero-init declarations (useful when a sensible default doesn't exist):

```c3
struct Config @mustinit { String path; int retries; }
Config c;                          // ERROR: must initialize
Config c = { "out.txt", 3 };       // ok
```

---

## Modules

```c3
// Module declaration (one per file, or multiple modules per file)
module myapp::net::http;

// Visibility
fn void public_fn() @public {}    // default: visible everywhere
fn void module_fn() @private {}   // visible only in this module
fn void file_fn()   @local {}     // visible only in this file

// Default visibility for entire module
module myapp::internal @private;  // all decls private by default

// Re-declaring the module mid-file switches the visibility context for what follows
module myapp;
fn void api_fn() {}            // public
module myapp @private;
fn void helper() {}            // private — same module, new section

// Group attributes into a custom one
attrdef @Hot = @inline, @export;
fn int fast_path(int x) @Hot { return x * 2; }

// Type references: no prefix needed if unambiguous
// Function calls: always need at least sub-module prefix
import std::math;
double x = math::sqrt(2.0);   // function: needs prefix
```

**Multi-file modules:** Multiple `.c3` files can share one module name. Imports are recursive — `import mylib` includes `mylib::net`, `mylib::io`, etc.

---

## Compile-Time Features

`$`-prefixed constructs run at compile time (inside macros/functions, not global scope):

```c3
// Compile-time if
$if env::WIN32:
    fn void init() { /* windows */ }
$else
    fn void init() { /* posix */ }
$endif

// @if on declarations (top-level conditional compilation)
fn void win_only() @if(env::WIN32) { }

// Compile-time reflection (0.8.0: $reflect provides .name, .qname, .offset, .alignment, .size)
macro print_fields($Type) {
    $foreach $field : $Type.membersof:
        io::printfn("%s @ offset %d", $reflect($field).name, $reflect($field).offset);
    $endforeach
}

// Compile-time constants
// $$FUNCTION  $$FILE  $$LINE  $$MODULE  $$DATE  $$TIME  $$VERSION  $$PRERELEASE

// File embedding
char[] data = $embed("assets/shader.glsl");
```

| Builtin / property | Purpose |
|---------|---------|
| `$Typeof(expr)` | Type of expression (capitalized in 0.8.0) |
| `$Typefrom(typeid)` | Type from a typeid (capitalized in 0.8.0) |
| `$defined(expr)` | Check if identifier/expression is well-formed |
| `$assert(cond)` | Compile-time assertion |
| `Type::size` / `Type::alignment` / `Type::kind` | Type properties (0.8.0 — replaces `Type.sizeof`, `.alignof`, `.kindof`) |
| `@sizeof(expr)` / `@alignof(expr)` / `@kindof(expr)` | Macro forms for expressions (0.8.0 — replaces `$sizeof` etc.) |
| `$reflect(field).{name, qname, offset, alignment, size}` | Member/type reflection (0.8.0) |
| `$eval("name")` | String → identifier |
| `$expand("expr")` | String → code (0.8.0) |
| `$feature(F)` | Check enabled feature flag |
| `$stringify(#expr)` | Capture a macro arg's source text as a string |
| `$defined($Type x = expr)` | Assignability check (replaces removed `$assignable`) |

> `$$`-prefixed identifiers (e.g. `$$acos`, `$$exp10`) are compiler-internal builtins. Use the stdlib wrappers (`math::acos`, etc.) instead.

For macros, generics, interfaces, operator overloading, and contracts, see `references/advanced.md`.

---

## Build System

```bash
c3c init myproject          # scaffold new project
c3c run                     # build & run (debug target)
c3c build release           # build named target
c3c test                    # run @test functions
c3c benchmark               # run @benchmark functions
c3c compile file.c3         # compile single file
c3c compile-run file.c3     # compile & run single file
c3c vendor-fetch            # download dependencies into lib/
c3c docgen                  # generate documentation (0.8.0 new)
```

**`project.json`:**
```json
{
  "version": "0.1.0",
  "langrev": "1",
  "sources": ["src/**"],
  "targets": {
    "debug":   { "type": "executable", "safe": true,  "opt": "O0" },
    "release": { "type": "executable", "safe": false, "opt": "O3", "strip-unused": true }
  }
}
```

### Verifying a snippet

When `c3c` is available, the cheapest way to check a self-contained snippet is `compile-run`:

```bash
c3c compile-run snippet.c3                  # builds + runs in one step
c3c compile-run snippet.c3 --use-stdlib=no  # for stdlib-free examples
```

Useful for sanity-checking small examples before handing them to the user. If `c3c` is not installed, say so explicitly rather than guessing.

---

## Testing

```c3
module mylib @test;

fn void test_add() @test {
    assert(add(1, 2) == 3);
}

fn void bench_add() @benchmark {
    for (int i = 0; i < 1000; i++) add(i, i+1);
}
```

Run with `c3c test` or `c3c benchmark`.

---

## Complete Example: File Line Counter

```c3
module wordcount;
import std::io;
import std::os;

fn int? count_lines(String path) {
    File f = file::open(path, "r")!;
    defer f.close();

    int lines = 0;
    while (try line = io::readline(&f)) {
        lines++;
    }
    return lines;
}

fn int main(String[] args) {
    if (args.len < 2) {
        io::printn("Usage: wordcount <file>");
        return 1;
    }
    int? n = count_lines(args[1]);
    if (catch err = n) {
        io::printfn("Error: %s", err);
        return 1;
    }
    io::printfn("Lines: %d", n);
    return 0;
}
```

---

## Common Pitfalls

| Error | Cause | Fix |
|-------|-------|-----|
| `No module named 'std::io'` | stdlib not found | Use `--use-stdlib=no` + `extern fn` |
| `Cannot cast 'char[64]' to 'char*'` | Fixed array ≠ pointer | Use `&array_name` |
| `Type.sizeof not found` | 0.8.0 renamed property accessors | Use `Type::size` (also `::alignment`, `::kind`) |
| `$sizeof undefined` | Removed in 0.8.0 | Use `@sizeof(expr)` macro, or `Type::size` |
| `$typeof undefined` | Renamed in 0.8.0 | Use `$Typeof` (capital T) |
| `Functions must be prefixed` | Missing module prefix | Add `module::fn_name()` |
| `'fn' is a keyword` | `fn` used as param name | Rename parameter |
| Implicit fallthrough | Coming from C habits | C3 switch auto-breaks; use `nextcase` |
| `a & b == c` parses unexpectedly | C3 bitwise ops bind **tighter** than `+ - == <`, opposite of C | Always parenthesize bitwise: `(a & b) == c`. All bitwise ops share one precedence level — `(a \| b) ^ c` not `a \| b ^ c`. |
| `int x = (int)f` required for float | C3 forbids implicit narrowing/float→int | Use explicit cast for any narrowing or float→int conversion. |
| Stale optional unhandled | Forgot `!` or `??` | Handle or propagate optional result |
| Module import not found | Wrong path separator | Use `::` not `/` or `.` |
| `usz undefined` | Renamed `sz` in 0.8.0 | Use `sz` (single signed-size type) |
| Using an enum as a bitmask | Enums aren't bit flags | Use `bitstruct` instead |

## Key Differences from C

| C | C3 |
|---|-----|
| `#include` / headers | `import` + modules |
| Preprocessor macros | `$if`, semantic macros |
| `typedef struct Foo Foo` | Just `struct Foo` |
| `int arr[4]` | `int[4] arr` (size left of name) |
| `errno` / return codes | Optional `?` types |
| Implicit switch fallthrough | Explicit `nextcase` required |
| `int32_t` (stdint) | `int` is always 32 bits |
| `size_t` / `ptrdiff_t` | `sz` |
| No generics | Ad-hoc generics: `struct Stack <Type>` / `Stack{int}` |
| No interfaces | `interface` + `any` |
| No defer | `defer` built-in |
| No contracts | `@require` / `@ensure` |

For full coverage of the standard library, see `references/stdlib.md`. For pre-0.8 code, see `references/migration_0_7_to_0_8.md`.
