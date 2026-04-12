---
name: c3-lang
description: Use when writing, debugging, or reviewing C3 language code; generating C3 programs, modules, or build configurations; or answering questions about C3 syntax, types, error handling, or compiler usage
---

# C3 Programming Language

## Overview

C3 is a systems programming language — "an evolution, not a revolution" over C. It keeps C's mental model and ABI compatibility while adding modules, optionals, slices, defer, generics, and compile-time features. Compiler: `c3c` (LLVM backend). Current version: **0.7.11**.

**Core principles:** Procedural, minimalist, data is inert, zero-is-initialization (ZII — zero value is always valid), no GC, no borrow checker, seamless C interop.

Resources: [c3-lang.org](https://c3-lang.org) · [github.com/c3lang/c3c](https://github.com/c3lang/c3c) · [Discord](https://discord.gg/qN76R87)

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
isz    usz                         // size type (like ptrdiff_t / size_t)

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

typedef MyInt = int;          // distinct type (no implicit conversion)
alias MyPtr = int*;           // transparent alias (like C typedef)
```

### Functions and Methods
```c3
fn int add(int a, int b) { return a + b; }

// Method: receiver type before dot, pointer receiver for mutation
fn void Point.translate(Point* self, int dx, int dy) {
    self.x += dx;
    self.y += dy;
}

// Named arguments
add(a: 1, b: 2);

// Variadic
fn void log(String fmt, args...) { io::printfn(fmt, ...args); }
```

### Structs and Enums
```c3
struct Point { int x; int y; }  // no trailing semicolon

enum Status : uint { IDLE, BUSY, DONE }  // backed by uint

// Enum with associated values (0.7.10+)
enum Shape {
    CIRCLE = { float radius },
    RECT   = { float w, h }
}

// Bitstruct (replaces C bitfields)
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
int[] s = arr[1..4];   // indices 1, 2, 3 (exclusive end)
int[] s2 = arr[1:3];   // same: start + count
usz len = s.len;       // slice length

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
    return file::read_all(path)!;  // ! re-throws any fault from read_all
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

    // Pattern 3: default value with ??
    String cfg = read_file("optional.cfg") ?? "default";

    // Pattern 4: force unwrap (panic if empty) !!
    String must = read_file("required.cfg")!!;

    // Pattern 5: if(try) happy-path check
    if (try s = read_file("maybe.txt")) {
        io::printfn("Got: %s", s);
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
    int* temp = tmalloc(int.sizeof * 100);
    String s = string::tformat("hello %s", name);
    DString ds;
    ds.tinit();
    // all allocations freed automatically on scope exit
};

// defer for cleanup (runs on any exit — return, break, error)
fn void? process(String path) {
    File! f = file::open(path, "r")!;
    defer f.close();
    // ... f is closed even if we return early or fault
}
```

**Allocator naming:**
- `mem::new(T)` / `mem::tnew(T)` — heap / temp
- `mem::new_array(T, n)` / `mem::temp_array(T, n)` — heap / temp array
- `@clone(v)` / `@tclone(v)` — heap / temp clone
- `mem::free(p)` — deallocate
- `destroy(x)` — deallocate + close resources (files, etc.)

**ZII principle:** Design structs so the zero value is valid. Use `= {}` or just declare — it's zeroed.

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

// Compile-time reflection
macro print_fields($Type) {
    $foreach $field : $Type.membersof:
        io::printfn("%s @ offset %d", $field.nameof, $field.offsetof);
    $endforeach
}

// Compile-time constants
// $$FUNCTION  $$FILE  $$LINE  $$MODULE  $$DATE  $$TIME  $$VERSION  $$PRERELEASE

// File embedding
char[] data = $embed("assets/shader.glsl");
```

| Builtin | Purpose |
|---------|---------|
| `$typeof(expr)` | Type of expression |
| `$defined(expr)` | Check if identifier exists |
| `$assert(cond)` | Compile-time assertion |
| `$sizeof(T)` | Size of type (compile-time) |
| `$alignof(T)` | Alignment |
| `$offsetof(T.field)` | Field offset |
| `$eval("name")` | String → identifier |
| `$evaltype("T")` | String → type |
| `$feature(F)` | Check enabled feature flag |

---

## Macros

```c3
// Basic macro (compile-time params use $ prefix)
macro max($Type)(a, b) {
    return a > b ? a : b;
}
max(int)(3, 5);  // → 5

// Unevaluated expression (#param) — argument is not evaluated before passing
macro measure(#expr) {
    usz start = clock();
    #expr;
    return clock() - start;
}
measure(some_expensive_fn());

// At-macros (@name) manage scopes
macro @swap(&a, &b) {
    var tmp = a;
    a = b;
    b = tmp;
}
@swap(x, y);
```

Macros with only `$`-prefixed params execute entirely at compile time.

---

## Generics

```c3
// Ad-hoc generic type (0.7.9+, preferred over module-based generics)
struct Stack <Type> {
    usz capacity;
    usz size;
    Type* elems;
}

fn void Stack.push(Stack* self, Type element) { /* ... */ }
fn Type Stack.pop(Stack* self) { /* ... */ }

// Instantiation
alias IntStack = Stack{int};
IntStack s;
s.push(42);
int val = s.pop();
```

---

## Interfaces and Dynamic Dispatch

```c3
interface Drawable {
    fn void draw(self);
}

struct Circle (Drawable) {    // Circle implements Drawable
    float radius;
}

fn void Circle.draw(Circle* self) @dynamic {
    io::printfn("Circle r=%f", self.radius);
}

// Dynamic dispatch via any type (typeid + void*)
fn void render(any obj) {
    Drawable d = (Drawable)obj;
    if (&d.draw) {    // check method exists at runtime
        d.draw();
    }
}

Circle c = { .radius = 5.0 };
render(&c);
```

---

## Operator Overloading

```c3
struct Vec2 { float x, y; }

fn Vec2 Vec2.add(self, Vec2 other) @operator(+) {
    return { self.x + other.x, self.y + other.y };
}

fn bool Vec2.equals(self, Vec2 other) @operator(==) {
    return self.x == other.x && self.y == other.y;
}

// Subscript
fn int List.get(self, usz idx) @operator([]) { return self.data[idx]; }
fn void List.set(self, usz idx, int val) @operator([]=) { self.data[idx] = val; }
```

Supported: `+ - * / % & | ^ ~ << >> == != < <= > >= [] []=`

---

## Contracts (Design by Contract)

```c3
<*
  @param n : "must be positive and under 1000"
  @require n > 0, n < 1000
  @ensure return > 0
*>
fn int process(int n) { return n * 10; }

fn int compute(int x) @pure { return x * x; }  // no side effects
```

In **safe mode** (`"safe": true` in project.json): contracts → runtime assertions.  
In **fast mode**: contracts → optimizer hints (assumed true, no runtime cost).  
Compile-time-evaluable contracts → always checked at compile time.

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

**Single-file (no stdlib):**
```bash
c3c compile file.c3 --use-stdlib=no
c3c compile-run file.c3 --use-stdlib=no
```

---

## C Interop

```c3
// Declare C functions
extern fn int printf(char* format, ...);
extern fn void* malloc(usz size);
extern fn void  free(void* ptr);
extern fn int   strcmp(char* a, char* b);

// Pass fixed array to C function (& gets pointer to first element)
char[64] buf;
printf("%s\n", &buf);

// Export C-callable function
fn int my_func(int x) @export @cname("my_c_func") { return x * 2; }
```

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

faultdef OPEN_FAILED;

fn int? count_lines(String path) {
    File! f = file::open(path, "r")!;
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
| `@sizeof not found` | Wrong sizeof syntax | Use `Type.sizeof` (not `@sizeof`) |
| `Functions must be prefixed` | Missing module prefix | Add `module::fn_name()` |
| `'fn' is a keyword` | `fn` used as param name | Rename parameter |
| Implicit fallthrough | Coming from C habits | C3 switch auto-breaks; use `nextcase` |
| Stale optional unhandled | Forgot `!` or `??` | Handle or propagate optional result |
| Module import not found | Wrong path separator | Use `::` not `/` or `.` |

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
| `size_t` | `usz` |
| `ptrdiff_t` | `isz` |
| No generics | Generic modules `Stack{int}` |
| No interfaces | `interface` + `any` |
| No defer | `defer` built-in |
| No contracts | `@require` / `@ensure` |
