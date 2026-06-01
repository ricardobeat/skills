---
name: c3-lang
description: Use whenever C3 (the systems language by Christoffer Lernö) appears — writing, reading, debugging, porting, or reviewing `.c3` source; setting up `project.json` / `c3c` builds; explaining C3 syntax, modules, optionals, faults, defer, allocators, macros, or stdlib APIs. Trigger even when the user only mentions `c3c`, "C3 lang", a `.c3` filename, or pastes code with `module`, `fn`, `faultdef`, or `?`-suffixed types. Covers C3 **0.8.0** and later.
---

# C3 Programming Language

C3 is a systems language — "an evolution, not a revolution" over C. Keeps C's mental model and ABI compatibility while adding modules, optionals, slices, defer, generics, and compile-time features. Compiler: `c3c` (LLVM backend). **Baseline: 0.8.0** (2026-05-12) — all docs and examples here target 0.8.0+.

**Core principles:** Procedural, minimalist, ZII (zero value is always valid), no GC, no borrow checker, seamless C interop. Naming is enforced by the lexer, not convention.

Resources: [c3-lang.org](https://c3-lang.org) · [github.com/c3lang/c3c](https://github.com/c3lang/c3c) · [Discord](https://discord.gg/qN76R87)

**Docs:** [Language Fundamentals](https://c3-lang.org/language-fundamentals/variables/) · [Optionals (Essential)](https://c3-lang.org/language-common/optionals-essential/) · [Optionals (Advanced)](https://c3-lang.org/language-common/optionals-advanced/) · [Generics & Macros](https://c3-lang.org/generic-programming/generics/) · [Misc Advanced](https://c3-lang.org/misc-advanced/asm/) · [Stdlib source](https://github.com/c3lang/c3c/tree/v0.8.0/lib/std)

**Reference files (load on demand):**
- `references/stdlib.md` — full stdlib API (io, collections, math, threads, encoding, …)
- `references/advanced.md` — macros, generics, interfaces, operator overloading, contracts
- `references/c_interop.md` — calling C, exporting C-callable symbols

---

## Syntax Cheatsheet

### Naming (enforced by grammar)
| Style | Used for |
|-------|----------|
| `UpperCamelCase` | Types, interfaces, faults |
| `snake_case` | Functions, variables, struct members |
| `ALL_CAPS` | Constants, enum values |
| `$lower` | Compile-time variables (macros only) |
| `#param` | Unevaluated expression parameters (macros) |

### Primitives
```c3
ichar  short  int  long  int128    // signed: 8, 16, 32, 64, 128 bits
char   ushort uint ulong uint128   // unsigned
iptr   uptr                        // pointer-sized
sz                                 // size type (like size_t)

float16  bfloat16  float  double  float128

bool  void  any  typeid
```

### Declarations
```c3
module myapp::utils;          // required for projects
import std::io;               // recursive by default
import std::collections::list @norecurse;

int x = 42;
const int MAX = 100;
int[] arr = { 1, 2, 3 };      // slice literal
int[4] fixed = { 1, 2, 3, 4 }; // fixed-size array (size left of name)

typedef MyInt = int;          // distinct type (no implicit conversion)
typedef MyId @constinit = int; // accept literals: get_by_id(1)
alias  MyPtr = int*;          // transparent alias
```

### Functions and Methods
```c3
fn int add(int a, int b) { return a + b; }

// Method: receiver before dot; &self = pointer receiver
fn void Point.translate(&self, int dx, int dy) {
    self.x += dx; self.y += dy;
}
fn int Point.dist_sq(&self) { return self.x*self.x + self.y*self.y; }

add(a: 1, b: 2);                          // named arguments
fn void log(String fmt, args...) { io::printfn(fmt, ...args); }  // variadic
fn int square(int x) => x * x;            // short body
```

### Structs and Enums
```c3
struct Point { int x; int y; }

enum Status : uint { IDLE, BUSY, DONE }   // backed by uint

// Inside an expression of known enum type, the prefix is inferred:
Status s = ok ? DONE : IDLE;
if (s == BUSY) { ... }

// Enum with associated values
enum Shape {
    CIRCLE = { float radius },
    RECT   = { float w, h }
}
// Reflection: Shape.values, Shape.names, Shape.len, Shape.membersof

// Use bitstruct for bit flags — NOT an enum
bitstruct Flags : short {
    bool read_only : 0;
    bool hidden    : 1;
    int  priority  : 2..4;
}

union IntOrFloat { int i; float f; }

Point p = { .x = 1, .y = 2 };
draw({ .x = 5, .y = 10 });               // struct literal in call
```

### Control Flow
```c3
// switch — NO implicit fallthrough; empty case falls to next non-empty
switch (status) {
    case IDLE:
    case BUSY:  io::printn("Not done");   // IDLE falls through here
    case DONE:  io::printn("Done");       // auto-breaks
    default:    io::printn("Unknown");
}

switch { case x > 100: ...; default: ...; }  // expression switch

// nextcase (explicit fallthrough)
switch (c) { case 'a': nextcase 'A'; case 'A': io::printn("A or a"); }

for (int i = 0; i < n; i++) { ... }
foreach (value : arr) { ... }
foreach (index, value : arr) { ... }
foreach (&value : arr) { *value *= 2; }   // by reference
foreach_r (value : arr) { ... }           // reverse

outer: for (...) { inner: for (...) { break outer; } }
```

### Pointers, Arrays, Slices
```c3
int* ptr = &value;    int deref = *ptr;    *ptr = 100;

// Slices (preferred over pointer+length)
int[] s  = arr[1..3];  // ..end is INCLUSIVE → indices 1,2,3
int[] s2 = arr[1:3];   // start:length → 3 elements from index 1
int[] s3 = arr[..];    int[] s4 = arr[..4];   int[] s5 = arr[1..];
int last = arr[^1];    // ^n: reverse-index; ^1 = last element
sz len = s.len;

// Fixed array → pointer (no automatic decay)
int[4] fixed;
takes_ptr(&fixed);     // & gets pointer to first element

String hello = "world";
char* cstr = hello.ptr;
```

---

## Error Handling (Optionals)

`T?` is either a `T` value or a **fault** (empty optional). Zero overhead vs. exceptions. Optionals cannot appear as function parameters — use `Maybe{T}` from `std::collections::maybe` to store them in structs.

```c3
faultdef FILE_NOT_FOUND, PERMISSION_DENIED;

fn String? read_file(String path) {
    if (!file::exists(path)) return FILE_NOT_FOUND~;  // ~ converts fault → empty optional
    return file::load_temp(path)!;                     // ! re-throws any fault
}

fn void main() {
    // catch
    String? result = read_file("data.txt");
    if (catch err = result) {
        switch (err) { case FILE_NOT_FOUND: io::printn("Not found"); default: io::printfn("Error: %s", err); }
        return;
    }
    io::printfn("Content: %s", result);  // unwrapped here

    String content = read_file("cfg.txt")!;           // rethrow
    String cfg = read_file("optional.cfg") ?? "default"; // or-else
    String must = read_file("required.cfg")!!;        // force unwrap (panic if empty)

    if (try s = read_file("a.txt") && try b = read_file("b.txt")) { ... }  // happy-path
}
```

| Operator | Meaning |
|----------|---------|
| `~` | Convert fault value → empty optional |
| `!` | Rethrow: propagate fault to caller |
| `??` | Or-else (binds tighter than arithmetic) |
| `!!` | Force unwrap: panic if empty |
| `@catch(x)` | Get the fault value |
| `@ok(x)` | `true` if value is present |

---

## Memory Management

```c3
// Stack
int[1024] buf;

// Heap
int* arr = mem::new_array(int, n);    // zero-initialized
int* raw = mem::alloc_array(int, n);  // uninitialized
mem::free(arr);

// Temporary allocator — all allocations freed at @pool() exit
// IMPORTANT: never return temp-allocated values past the @pool scope
@pool() {
    int* temp = tmalloc(int::size * 100);
    String s = string::tformat("hello %s", name);
    DString ds; ds.tinit();
};

// defer runs on any exit — return, break, or fault
fn void? process(String path) {
    File f = file::open(path, "r")!;
    defer f.close();
    defer try io::printn("ok");          // only on normal exit
    defer catch io::printn("failed");    // only on fault exit
}
```

**Key allocator names:**
- `mem::new(T)` / `mem::tnew(T)` — heap / temp single value
- `mem::new_array(T, n)` / `mem::temp_array(T, n)` — heap / temp array
- `@clone(v)` / `@tclone(v)` — heap / temp clone
- `mem::free(p)` — deallocate
- `destroy(x)` — deallocate + close resources

**ZII:** Structs zero-init by default. Add `@mustinit` to forbid it:
```c3
struct Config @mustinit { String path; int retries; }
Config c = { "out.txt", 3 };  // must initialize explicitly
```

---

## Modules

```c3
module myapp::net::http;

fn void public_fn() @public {}    // default: visible everywhere
fn void module_fn() @private {}   // visible only in this module
fn void file_fn()   @local {}     // visible only in this file — cannot be overridden

// Asymmetry: types don't need a prefix when unambiguous, but functions always do
import std::math;
double x = math::sqrt(2.0);       // functions always need module prefix
```

**Imports are recursive** — `import mylib` includes `mylib::net`, `mylib::io`, etc. Use `@norecurse` to opt out.

```c3
// Group attributes
attrdef @Hot = @inline, @export;
fn int fast_path(int x) @Hot { return x * 2; }
```

---

## Compile-Time Features

```c3
$if env::WIN32:
    fn void init() { /* windows */ }
$else
    fn void init() { /* posix */ }
$endif

fn void win_only() @if(env::WIN32) { }   // @if on declarations

// Compile-time reflection
macro print_fields($Type) {
    $foreach $field : $Type.membersof:
        io::printfn("%s @ offset %d", $reflect($field).name, $reflect($field).offset);
    $endforeach
}

char[] data = $embed("assets/shader.glsl");  // file embedding
```

| Builtin | Purpose |
|---------|---------|
| `$Typeof(expr)` | Type of expression |
| `$Typefrom(typeid)` | Type from a typeid |
| `$defined(expr)` | Check if identifier is well-formed |
| `$assert(cond)` | Compile-time assertion |
| `Type::size` / `::alignment` / `::kind` | Type properties |
| `@sizeof(expr)` / `@alignof(expr)` / `@kindof(expr)` | Expression forms |
| `$reflect(field).{name,qname,offset,alignment,size}` | Member reflection |
| `$eval("name")` | String → identifier |
| `$expand("expr")` | String → code |
| `$feature(F)` | Check enabled feature flag |
| `$stringify(#expr)` | Capture macro arg source as string |
| `$$FUNCTION` `$$FILE` `$$LINE` `$$MODULE` | Compiler builtins |

For macros, generics, interfaces, and operator overloading, see `references/advanced.md`.

---

## Build System

```bash
c3c init myproject          # scaffold new project
c3c run                     # build & run (debug)
c3c build release           # build named target
c3c test                    # run @test functions
c3c compile-run file.c3     # compile & run single file (good for snippets)
c3c vendor-fetch            # download dependencies into lib/
c3c docgen                  # generate documentation
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

Verify a snippet: `c3c compile-run snippet.c3` (add `--use-stdlib=no` for stdlib-free examples). If `c3c` is not installed, say so explicitly.

`c3fmt` formats `.c3` files; copy `assets/.c3fmt` into the project root first.

---

## Testing

```c3
module mylib @test;

fn void test_add() @test { assert(add(1, 2) == 3); }
fn void bench_add() @benchmark { for (int i = 0; i < 1000; i++) add(i, i+1); }
```

Run with `c3c test` / `c3c benchmark`.

---

## Complete Example

```c3
module wordcount;
import std::io;

fn int? count_lines(String path) {
    File f = file::open(path, "r")!;
    defer f.close();
    int lines = 0;
    while (try line = io::readline(&f)) { lines++; }
    return lines;
}

fn int main(String[] args) {
    if (args.len < 2) { io::printn("Usage: wordcount <file>"); return 1; }
    int? n = count_lines(args[1]);
    if (catch err = n) { io::printfn("Error: %s", err); return 1; }
    io::printfn("Lines: %d", n);
    return 0;
}
```

---

## Common Pitfalls

| Error | Fix |
|-------|-----|
| `Cannot cast 'char[64]' to 'char*'` | Use `&array_name` (fixed array ≠ pointer, no decay) |
| `Functions must be prefixed` | Add `module::fn_name()` — functions always need prefix |
| Implicit switch fallthrough | C3 auto-breaks; use `nextcase` for explicit fallthrough |
| `a & b == c` parses unexpectedly | Bitwise ops bind **tighter** than `+ - == <` (opposite of C) — always parenthesize: `(a & b) == c` |
| Implicit narrowing / float→int | C3 forbids it — use explicit cast |
| `??` precedence surprise | `??` binds tighter than arithmetic: `f() ?? x + 1` is `(f() ?? x) + 1` |
| Temp data outlives `@pool()` | Copy results out of the `@pool` block before it closes |
| `#param` evaluated multiple times | `#expr` args aren't memoized — side effects happen per use |
| Returning dangling slice | Slice lifetime is tied to the underlying pointer — don't return slices of stack/temp data |
| `String name = read_file(...)` | Doesn't handle the optional — missing `!`, `??`, or `catch` |
| Using an enum as a bitmask | Use `bitstruct` instead |
| Enum arithmetic | `++`/`--` step with wrap-around; for ordinal math use `.ordinal` |

## Key Differences from C

| C | C3 |
|---|-----|
| `#include` / headers | `import` + modules |
| Preprocessor macros | `$if`, semantic macros |
| `typedef struct Foo Foo` | Just `struct Foo` |
| `int arr[4]` | `int[4] arr` (size left of name) |
| `errno` / return codes | Optional `?` types |
| Implicit switch fallthrough | Explicit `nextcase` required |
| `int32_t` | `int` is always 32 bits |
| `size_t` / `ptrdiff_t` | `sz` |
| No generics | `struct Stack <Type>` / `Stack{int}` |
| No interfaces | `interface` + `any` |
| No defer | `defer` built-in |
| No contracts | `@require` / `@ensure` |
| Bitwise ops lower precedence than `==` | Bitwise ops **higher** precedence than `==` |
| Octal literals (`0123`) | Removed — use `0o123` if needed |

For the full stdlib, see `references/stdlib.md`. For C interop, see `references/c_interop.md`.
