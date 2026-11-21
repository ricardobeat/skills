---
name: c3-lang
description: Use when writing, debugging, reviewing, or migrating C3 code (.c3), invoking c3c/c3fmt, editing project.json or .c3l manifests, resolving C3 build errors, or choosing C3 standard-library APIs, even when the user only mentions a C3 file or compiler message. Defaults to C3 0.8.6.
---

# C3 Programming Language

C3 is a C-ABI-compatible systems language with modules, optionals, slices, contracts, defer, generics, and structured compile-time programming. Compiler: `c3c` (LLVM backend; experimental C backend). Baseline: **0.8.6**.

The grammar enforces casing: user-defined types start uppercase with at least one lowercase letter (`Point`, not `P` or `POINT`); functions, variables, and fields start lowercase (conventionally `snake_case`); constants, enum values, and faults are `CONSTANT_CASE`.

- **Resources:** [c3-lang.org](https://c3-lang.org) · [github.com/c3lang/c3c](https://github.com/c3lang/c3c) · [Discord](https://discord.gg/qN76R87)
- **Docs:** [Single-page manual](https://c3-lang.org/all/) · [Optionals](https://c3-lang.org/language-common/optionals-essential/) · [Generics](https://c3-lang.org/generic-programming/generics/) · [Attributes](https://c3-lang.org/language-common/attributes/) · [Project config](https://c3-lang.org/build-your-project/project-config/) · [Library packaging](https://c3-lang.org/misc-advanced/library-packaging/) · [Stdlib source](https://github.com/c3lang/c3c/tree/v0.8.6/lib/std)

**Local references:**
- `references/ownership.md` — allocator lifetimes, `@pool()`/`tmem`, `@stack_mem`, `defer`/`defer catch`, leak and `VMEM_TEMP` checks
- `references/stdlib.md` — curated standard-library guide
- `references/stdlib/index.txt` — namespace index for the `references/stdlib/<namespace>.txt` 0.8.6 API snapshots
- `references/advanced.md` — macros, generics, interfaces, reflection, operator overloading, contracts
- `references/c_interop.md` — declaring C symbols, exporting symbols, linking, assembly names
- `references/build-and-dependencies.md` — `project.json` targets, dependency fetching, `.c3l` source libraries
- `references/debugging-with-lldb.md` — breakpoints, stepping, inspecting variables, safe-mode traps

To locate the installed standard library source, run `c3c compile --build-env` (or inspect `<repo>/lib/std` in a compiler checkout).

---

## Syntax Basics

```c3
module myapp::utils;          // required in projects
import std::io;               // recursive by default

int x = 42;
const int MAX = 100;
int[] arr = { 1, 2, 3 };      // slice
int[4] fixed = { 1, 2, 3, 4 }; // fixed array (size left of name)

typedef MyInt = int;           // distinct type; no implicit conversion
typedef MyId @constinit = int; // distinct type that accepts literals
typedef CStr = inline char*;   // implicitly converts to char*, not from char*
alias MyPtr = int*;            // transparent rename (same type)

fn int add(int a, int b = 1) { return a + b; }
fn int square(int x) => x * x; // short body
int sum = add(a: 1, b: 2);     // named arguments

struct Point { int x; int y; }
fn void Point.translate(&self, int dx, int dy) { self.x += dx; self.y += dy; } // &self = pointer receiver
Point p = { .x = 1, .y = 2 };

// Enums are contiguous ordinals starting at 0 and can carry associated values
enum Status : uint (String label) {
    IDLE { "idle" },
    BUSY { "busy" },
    DONE { "done" },
}

// Non-contiguous constant sets use constset
constset HttpCode : int {
    OK = 200,
    NOT_FOUND = 404,
}

bitstruct Flags : short {
    bool read_only : 0;
    bool hidden    : 1;
    int priority   : 2..4;
}

// C ABI interop
extern fn CInt puts(ZString s);
fn int double_it(int v) @export("c3_double_it") => v * 2;
```

### Control Flow

```c3
// switch auto-breaks; stacked empty cases share a body
switch (s) {
    case IDLE:
    case BUSY:
        io::printn("Not done");
    case DONE:
        io::printn("Done");
}

// Explicit fallthrough or jump to another case with nextcase
switch (c) {
    case 'a':
        nextcase 'A';
    case 'A':
        io::printn("A or a");
}

foreach (value : arr) { ... }
foreach (index, value : arr) { ... }
foreach (&value : arr) { *value *= 2; } // by reference
foreach_r (value : arr) { ... }         // reverse
```

Loops, `if`, and `switch` accept labels (`for OUTER: (...) { break OUTER; }`). Single-statement `else if` bodies require braces: `else if (cond) { ... }`.

### Pointers, Slices, and Strings

```c3
int* ptr = &value;

int[] s  = arr[1..3]; // inclusive end: indices 1, 2, 3
int[] s2 = arr[1:3];  // start:length
int[] s3 = arr[..];
int last = arr[^1];   // reverse index
sz len = s.len;

int[4] fixed;
takes_ptr(&fixed);    // int[4] does not decay to int*; &fixed (int[4]*) does

String hello = "world";
char* bytes = hello.ptr;
ZString cstr = hello.zstr_tcopy();
```

`String` is `typedef String @constinit = inline char[]`: it converts implicitly to `char[]`, while converting `char[]` to `String` needs an explicit `(String)` cast. A `String`'s `.ptr` is not guaranteed to be NUL-terminated; call `zstr_copy(mem)` or `zstr_tcopy()` before passing a string or subslice to a C API. `sz` (signed) and `usz` (unsigned) are the native size types.

---

## Error Handling (Optionals)

`T?` holds either a value of type `T` or an empty state carrying a `fault` (called an "Excuse" in the manual). It has no heap or exception-table overhead. Optionals are allowed on variables, expressions, and return types, but not in function or macro parameter declarations. Passing an optional expression to a regular parameter evaluates the call only if every argument has a value; otherwise it produces the first fault without calling the function. Use `Maybe{T}` for optional struct fields.

```c3
excuse FILE_NOT_FOUND, PERMISSION_DENIED;

fn String? read_file(String path) {
    if (!file::exists(path)) return FILE_NOT_FOUND~; // ~ wraps a fault as an empty optional
    return (String)file::load_temp(path)!;           // ! rethrows; cast char[] -> String
}

String? r = read_file("a.txt");
if (catch err = r) { ... }              // inspect fault
String s = read_file("b.txt")!;         // rethrow to caller
String t = read_file("c.txt") ?? "x";   // or-else (tighter than +/-, looser than */%)
String u = read_file("d.txt")!!;        // force unwrap (panic if empty)
if (try a = read_file("e.txt") && try b = read_file("f.txt")) { ... }
```

| Operator / form | Meaning |
|-----------------|---------|
| `~` | fault → empty optional |
| `!` | rethrow to caller |
| `??` | fallback value if empty |
| `!!` | force unwrap (panic if empty) |
| `if (catch err = x)` | catch and inspect fault |
| `if (try val = x)` | unwrap on success |

Declare faults with `excuse`. Faults from another module must be module-qualified (`io::FILE_NOT_FOUND`, never bare `FILE_NOT_FOUND`).

After `if (catch err = x) { return; }`, `x` narrows to its unwrapped type for the rest of the scope — use `x` directly without `!!`.

Discarding any optional return value (including `void?`) is a compile error unless the callee is marked `@maydiscard` or you cast explicitly with `(void)call()`. `void?` is valid only as a return type; capture its fault with `fault f = @catch(expr)` or `if (catch f = expr)`, then branch with `switch (f)`.

---

## Memory

```c3
// Heap: new_array zero-inits and returns a slice; alloc_array leaves uninit
int[] arr = mem::new_array(int, n);
mem::free(arr);

// Temp allocator: freed when @pool() exits; never return temp data past the block
@pool() {
    String s = string::tformat("hello %s", name);
};

// Stack-first scratch with automatic heap spillover (add ~32B slack for header/align)
@stack_mem(256; Allocator smem) {
    if (try buf = alloc::alloc_array_try(smem, char, needed)) { ... }
};

// defer is block-scoped and runs LIFO on every exit
fn void? process(String path) {
    File f = file::open(path, "r")!;
    defer f.close();                  // File.close is @maydiscard; other void? calls need (void)
    defer try io::printn("ok");       // normal exit only
    defer catch io::printn("failed"); // fault exit only
}

// Structs zero-init by default; @mustinit disallows @noinit
struct Config @mustinit { String path; int retries; }
```

Key allocators: `mem::new(T)` / `mem::tnew(T)`, `mem::new_array(T, n)` / `mem::temp_array(T, n)`, `mem::alloc_array(T, n)` / `mem::talloc_array(T, n)`, `alloc::alloc_array_try(a, T, n)`, `@clone(v)` / `@tclone(v)`, `mem::free(p)`. Verify lifetimes in tests with `mem::@assert_leak() { ... };` (`"MEMORY_ASSERTS"`) and `"VMEM_TEMP"` on debug/ASan targets. See `references/ownership.md` for ownership patterns, rollback idioms, and allocator rules.

---

## Contracts, Safety, and Builds

Contracts live in doc-comment blocks (`<* ... *>`) directly above a declaration:

```c3
<*
 @require x > 0 : "x must be positive"
 @ensure return > x
*>
fn int bump(int x) => x + 1;
```

Safety checks are controlled by `--safe=yes|no` (`-O0` and `-O1` default safe; `-O2` and higher default unsafe):

- **Safe** traps with a trace on division by zero, out-of-bounds indexing, null dereference, `assert` and contract failure, and `unreachable()`.
- **Unsafe** removes those checks and lets the optimizer assume they hold.

Behavior defined where C leaves UB: signed integer overflow wraps (two's complement), and narrowing casts truncate silently. Locals zero-init by default; `@noinit` opts out and leaves stack memory uninitialized. Structs and fixed arrays are value types and copy on assignment.

Idioms: prefer `String` and slices over raw pointer+length; prefer free functions over methods; restrict `!!` to `main`, tests, and provably impossible paths; take an `Allocator` in library code; use the temp allocator for call-scoped data; mark hot cross-module functions `@inline`.

---

## Generics, Macros, and Compile-Time

Generics declare parameters in `<>` and instantiate them in `{}`:

```c3
struct Stack <Type> {
    Type[] items;
}
fn Type sum_all(Type[] arr) <Type> {
    Type total = 0;
    foreach (v : arr) total += v;
    return total;
}

Stack{int} st;
int total = sum_all{int}(arr);
```

Macros are compiler-checked and scoped (no text preprocessor). Parameter sigils: `$param` is a compile-time constant or type, `#param` is an unevaluated expression re-evaluated on every use, and a trailing `@body` receives a caller block. Macros using `#` parameters or `@body` must start with `@`:

```c3
macro @swap_vals(#a, #b) {
    var tmp = #a;
    #a = #b;
    #b = tmp;
}
```

Conditional compilation uses `@feat` at top level and `$if`/`$else`/`$switch` inside function or macro bodies:

```c3
// Top-level declarations use @feat (never $if/$endif)
fn void init() @feat(WIN32) { }
fn void init() @feat(!WIN32) { }

fn void setup() {
    $if env::WIN32:
        io::printn("win");
    $else
        io::printn("other");
    $endif
}

char[] data = $embed("assets/shader.glsl");
attrmacro @Hot = @inline, @export;
```

`$else` takes no colon (`$if cond:` … `$else` … `$endif`). There is no `$elseif`/`$elif`/`$else if`; nest another `$if` inside `$else`, or branch with `$switch:` / `$case cond:` / `$default:` / `$endswitch`.

Key compile-time operators and reflection: `$Typeof(expr)`, `$Typefrom(id)`, `$defined(expr)`, `$assert(cond)`, `Type::size` / `::alignment` / `::kind` / `::members` (with `$m.nameof`), `@sizeof(expr)`, `$reflect(expr).size` / `.alignment` / `.is_const`, `$eval("name")`, `$expand("stmt;")`, `$feat(F)`. Use `&&&` and `|||` when the right-hand side of a compile-time condition must not be type-checked on short-circuit. Access reflected fields with `a.$field` and `a.$field = b` (or `a.$eval($field)`).

`@feat(FLAG)` and `$feat(FLAG)` accept `&`, `|`, `!`, and parentheses; commas mean `|`, and repeated `@feat` attributes mean `&`. `@if` is restricted to generic declarations parameterized by generic arguments.

See `references/advanced.md` for detailed coverage of macros, generics, reflection, operator overloading, and contracts.

---

## Runtime Polymorphism (`any`, Interfaces)

`any` is a fat pointer (`ptr` + `type`), created implicitly from any pointer. Downcast by switching on `a.type` with bare type names (standalone type IDs use `Foo::typeid`):

```c3
switch (a.type) {
    case Foo:
        Foo* f = (Foo*)a.ptr;
    default:
        break;
}
```

Interfaces dispatch through interface metadata attached to `any` values. Implementing methods carry `@dynamic`; interface declarations omit the receiver. Mark optional interface methods `@optional` and test their function pointer before calling:

```c3
interface Greeter {
    fn String greet();
    fn String bye() @optional;
}

struct Foo (Greeter) { String name; }
fn String Foo.greet(&self) @dynamic => self.name;

Foo foo = { "hello" };
Greeter g = &foo;
io::printn(g.greet());
if (&g.bye) io::printn(g.bye());
```

A `@dynamic` method satisfies a matching interface even when the type does not declare it, including on built-in types. Prefer generics when types are known at compile time.

---

## Concurrency

`std::thread` wraps native OS threads with no runtime scheduler and no data-race checks. `import std::thread;` recursively imports `std::thread::channel`.

```c3
import std::thread;

Thread t;
t.create(&worker, arg)!!;
int code = t.join()!!; // or t.detach()!! — never both

Mutex m;
m.init()!!;
defer m.destroy();
m.@in_lock() {
    // unlocked at block exit
};

BufferedChannel{int}* ch = channel::create_buffered(mem, size: 16)!!;
defer ch.destroy();
ch.push(42)!!;
int v = ch.pop()!!;
```

Channels: `BufferedChannel` (ring buffer), `UnbufferedChannel` (one in-flight), `UnboundedChannel` (growable), `OneShotChannel` (single value). Channel faults: `CHANNEL_CLOSED`, `CHANNEL_BLOCKED`, `CHANNEL_EMPTY`. Dynamic thread pool: `std::thread::ThreadPool`.

---

## Modules

```c3
module myapp::net::http;

fn void pub_fn()  @public {}  // default
fn void priv_fn() @private {} // module-only
fn void file_fn() @local {}   // file-only, cannot be overridden
```

Imports are recursive (`import mylib` includes `mylib::net`, etc.); add `@norecurse` to opt out. Types can omit their module prefix when unambiguous; functions always require it.

---

## Build, Testing, and Tooling

```bash
c3c init myproject
c3c run                           # build and run default target
c3c build -O2                     # optimized build (or pass a target from project.json)
c3c compile-run file.c3           # compile and run standalone file
c3c compile-only --no-obj file.c3 # typecheck without emitting objects (or: c3c compile -C file.c3)
c3c test [target]
c3c benchmark [target]
c3c source-lib src/lib.c3 -o my_lib
c3c fetch <library>
c3c project fetch [library ...]
c3c vendor-fetch <library>
c3c docgen
```

`project.json` target types: `executable`, `static-lib`, `dynamic-lib`, `source-lib`, `object-files`, `prepare`, `benchmark`, `test`. Useful flags: `--safe=yes|no`, `--use-stdlib=no`, `--warn-unusedlocal=yes|error`, `--warn-unusedparam=yes|error`, `--stats=summary|full|json`. See `references/build-and-dependencies.md` for target settings, diagnostic features, and `.c3l` packaging.

Query the compiler for exhaustive lists: `c3c --list-project-properties`, `--list-manifest-properties`, `--list-attributes`, `--list-builtins`, `--list-keywords`, `--list-type-properties`, `--list-precedence`. Format code with `c3fmt` (a starter config lives at `assets/.c3fmt`). Check `references/stdlib/<namespace>.txt` or the installed stdlib source before relying on an unfamiliar standard-library signature, and verify edits with the narrowest relevant `c3c` command.

### Testing

```c3
fn void test_add() @test {
    assert(add(1, 2) == 3);
}

fn void bench_add() @benchmark {
    for (int i = 0; i < 1000; i++) add(i, i + 1);
}
```

Run with `c3c test [target]` or `c3c benchmark [target]`. `std::core::test` provides `test::eq`, `test::@check`, and `test::@error`.

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| `char[64]` won't pass as `char*` | Fixed arrays don't decay — pass `&array_name` (`char[64]*` converts to `char*`) |
| Function call fails without prefix | Functions always need `module::fn()` |
| Missing `switch` fallthrough | C3 auto-breaks; use `nextcase` for explicit fallthrough |
| `a & b == c` wrong result | Bitwise ops bind tighter than `==` (opposite of C) — parenthesize |
| `??` precedence surprise | `f() ?? x + 1` is `(f() ?? x) + 1` (`??` binds tighter than `+`/`-`, looser than `*`/`/`/`%`) |
| Temp data dies after `@pool()` | Copy results out before the block closes; enable `"VMEM_TEMP"` on debug/ASan targets to catch escapes |
| `if (cond) defer cleanup();` runs immediately | `defer` is block-scoped, not function-scoped — write `defer if (cond) cleanup();` |
| `defer cleanup();` fails on `void?` | Only `@maydiscard` calls can be discarded — write `defer (void)cleanup();` |
| `return` inside `@pool()` / `@stack_mem()` | Returns from the enclosing function, not the macro block — use `if (try ...)` to skip the rest of the block |
| Side effect in `assert(fn())` disappears in `-O2+` | `assert` is stripped in unsafe builds — call first, then `assert(ok)` or `if (!ok) unreachable(...)` |
| `mem::free` on a `libc::malloc` pointer | Never mix `libc` and `mem` allocators — breaks `TrackingAllocator` and `mem::@assert_leak()` |
| `mem::clear` after `mem::new_array` | `new_array`/`temp_array` already zero-init; use `alloc_array`/`talloc_array` when overwriting all elements |
| `mem::malloc` / `new_array` panics on OOM | Use `alloc::malloc_try` / `alloc::alloc_array_try` / `alloc::realloc_array_try` for fallible allocation |
| `#param` side effects repeat | `#expr` macro arguments are re-evaluated on each use |
| Dangling slice | Slice lifetime is tied to its backing storage — never return stack or temp slices |
| Unhandled optional | `String s = fn_returning_optional()` — handle with `!`, `??`, `if (try ...)`, or `if (catch ...)` |
| `char[]` won't convert to `String` | `String` is `inline char[]` — cast explicitly with `(String)bytes` |
| Enum as bitmask | Use `bitstruct` instead |
| Enum arithmetic | Use `.ordinal` for math; `++`/`--` wrap around |
| Implicit narrowing or float→int | Explicit cast required |
| Negative literal into wide unsigned (`ulong x = -1`) | Cast explicitly (`(ulong)-1` or `ulong::max`) |
| Signed/unsigned aggregate cast (`int[3]` ↔ `uint[3]`) | Cast explicitly across signed/unsigned arrays, slices, and vectors |
| `else if (x) foo();` rejected | Put single-statement `else if` bodies in braces: `else if (x) { foo(); }` |
| Duplicate designated initializer | `{ .a = 1, .a = 1 }` is a compile error |
| Empty infinite loop never panics | Opt-in in safe mode: `--infinite-loop-detect=yes` |
| Works in `-O0`, misbehaves in `-O2+` | Safe builds trap on UB; unsafe builds optimize assuming it doesn't happen — test both |
