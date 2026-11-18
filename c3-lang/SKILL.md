---
name: c3-lang
description: Use when writing, debugging, reviewing, or migrating C3 code (.c3), invoking c3c/c3fmt, editing project.json or .c3l manifests, resolving C3 build errors, or choosing C3 standard-library APIs, even when the user only mentions a C3 file or compiler message. Defaults to C3 0.8.6.
---

# C3 Programming Language

C3 is a systems language with modules, optionals, slices, defer, generics, and compile-time features. Compiler: `c3c` (LLVM backend; experimental C backend in 0.8.5+). **Baseline: 0.8.6.** PascalCase types, snake_case functions, and CONSTANT_CASE constants are required by the language.

Resources: [c3-lang.org](https://c3-lang.org) · [github.com/c3lang/c3c](https://github.com/c3lang/c3c) · [Discord](https://discord.gg/qN76R87)

**Docs:** [Single-page manual](https://c3-lang.org/all/) · [Optionals](https://c3-lang.org/language-common/optionals-essential/) · [Generics](https://c3-lang.org/generic-programming/generics/) · [Attributes](https://c3-lang.org/language-common/attributes/) · [Project config](https://c3-lang.org/build-your-project/project-config/) · [Library packaging](https://c3-lang.org/misc-advanced/library-packaging/) · [Stdlib source](https://github.com/c3lang/c3c/tree/v0.8.6/lib/std)

**Reference files (load on demand):**
- `references/stdlib.md` — curated stdlib guide; open only the sections needed for the task
- `references/stdlib/index.txt` — namespace index for the detailed signature snapshots
- `references/stdlib/<namespace>.txt` — public declaration snapshots generated with C3 0.8.6; check these before guessing an API
- `references/advanced.md` — macros, generics, interfaces, reflection, operator overloading, contracts
- `references/c_interop.md` — declaring C symbols, exporting symbols, linking, exact assembly names
- `references/build-and-dependencies.md` — project targets, dependency fetching, `.c3l` source libraries
- `references/debugging-with-lldb.md` — breakpoints, stepping, variables, traps

**Locating c3c sources & stdlib:** source checkout → `<repo>/lib/std`. Homebrew → `$(brew --prefix c3c)/lib/c3/std`. Linux installations vary; inspect `c3c --build-env` or the installed distribution rather than assuming a path.

---

## Working Rules

- Target C3 0.8.6 syntax. Run `c3c --version` before version-sensitive work.
- Read the relevant stdlib signature file or the installed standard-library source before using an uncertain API. The snapshots were generated on macOS arm64; check the installed source for other platform bindings. Do not infer C3 APIs from C++, Rust, or older C3 examples.
- For single files, verify with `c3c compile file.c3` or `c3c compile-run file.c3`. Use `compile-only` when linking is unavailable. For projects, run the narrowest relevant `c3c build`, `c3c test`, or `c3c run` target after changes.
- Keep allocator and error-propagation choices explicit. Free heap resources, bound `@pool()` lifetimes, and handle every optional before producing the final code.
- `c3fmt` formats source files. Copy `assets/.c3fmt` to the project root when the project has no formatter configuration.
- Use `c3c --list-project-properties`, `--list-manifest-properties`, `--list-attributes`, `--list-builtins`, and `--list-type-properties` for exhaustive compiler-provided lists.

**C3 0.8.6 state:** `@feat` / `$feat` accept feature lists, `excuse` / `constset` / `attrmacro` are the documented spellings, and `@asmname` preserves exact assembly symbol names. Source libraries and registry dependencies use `.c3l` packaging and checksum verification. `std::gfx`, `TreeSet`, `NonNull` / `Nullable`, cross-platform dylib helpers, and `file::open_fd` are available. Single-statement `else if` requires braces, and `std::encoding::experimental::regex` uses `IGNORE_CASE`, `NOT_BOL`, `NOT_EOL`, and `NO_MATCH` names.

---

## Syntax Cheatsheet

```c3
module myapp::utils;          // required for projects
import std::io;               // recursive by default

int x = 42;
const int MAX = 100;
int[] arr = { 1, 2, 3 };      // slice
int[4] fixed = { 1, 2, 3, 4 }; // fixed array (size left of name)

typedef MyInt = int;           // distinct type, no implicit conversion
typedef MyId @constinit = int; // also accepts literals
typedef CStr = inline char*;   // implicit → base type, not ←
alias MyPtr = int*;            // transparent alias — same type, pure rename

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
char* bytes = hello.ptr;
ZString cstr = hello.zstr_tcopy();
```

`String` is a byte slice. `bytes` is not necessarily NUL-terminated; use `zstr_copy(mem)` or `zstr_tcopy()` before passing an arbitrary string or subslice to a C API. `sz` is signed and `usz` is unsigned; both are valid size types.

---

## Error Handling (Optionals)

`T?` = result or an empty value carrying a `fault` (called an "Excuse" in current docs). Zero overhead. Optional types are allowed for variables, expressions, and returns, but not in function or macro parameter declarations. Passing an optional expression to an ordinary parameter is allowed: the call runs only if all arguments have results, otherwise it yields the first fault without calling the function. Use `Maybe{T}` when a struct field needs optional-like storage.

```c3
excuse FILE_NOT_FOUND, PERMISSION_DENIED;

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

Declare faults with `excuse`; `faultdef` is a compatibility spelling and `faultset` was removed in 0.8.5. Faults referenced from another module **must** be module-qualified: `kvcache::ALLOC_FAILED`, never bare `ALLOC_FAILED`.

After `if (catch err = x) { return; }`, `x` narrows to its plain value for the rest of the scope — use `x` directly, no `!!` needed.

`void?` is valid only as a return type — it has no variable form. Grab the fault from a call with `fault f = @catch(expr)`, or `if (catch f = expr)`, then branch with a plain `switch (f) { case SOME_FAULT: … }`.

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

// defer runs on every exit; multiple defers run last-to-first
fn void? process(String path) {
    File f = file::open(path, "r")!;
    defer f.close();
    defer try io::printn("ok");       // only on normal exit
    defer catch io::printn("failed"); // only on fault
}

// ZII: structs zero-init by default; @mustinit disallows @noinit
struct Config @mustinit { String path; int retries; }
```

Key allocators: `mem::new(T)` / `mem::tnew(T)`, `mem::new_array(T,n)` / `mem::temp_array(T,n)`, `@clone(v)` / `@tclone(v)`, `mem::free(p)`.

---

## Safety & Builds

Safe (debug) and fast (release) builds differ only in what a bug does at runtime.

- **Safe** traps, with a trace, on division by zero, out-of-bounds indexing, null deref, `assert`/contract failure, and `unreachable()`.
- **Fast** drops the checks; those same bugs become UB the optimizer assumes away.

Defined where C leaves it UB: signed overflow always wraps (two's complement); narrow casts truncate silently. Locals zero-init by default; `@noinit` opts out (reading an unassigned `@noinit` traps in safe builds). Structs and arrays are values — assignment copies.

Idioms: prefer `String`/slices over raw pointer+length; free functions over methods; `!!` only in `main`/tests/impossible paths; take an `Allocator` in library code; temp allocator for call-scoped data; `@inline` hot cross-module functions.

---

## Runtime Polymorphism (`any`, interfaces)

`any` is a fat pointer (data + typeid), created implicitly from any pointer. Downcast by switching on `a.type`.

```c3
switch (a.type) { case Foo.typeid: …; default: …; }   // `.typeid` optional in a case
```

Interfaces dispatch methods through interface metadata attached to `any` values, not by name lookup. Methods exposed for interface calls are marked `@dynamic`; interface declarations list signatures without a receiver.

```c3
interface Greeter { fn String greet(); }
struct Foo (Greeter) { int x; }
fn String Foo.greet(Foo* self) @dynamic => "hello";
Greeter g = (Greeter)a;
if (&g.greet) io::printn(g.greet());   // @optional methods need this check
```

`@dynamic` methods satisfy an interface without the type declaring it — works on built-ins too. Prefer generics (zero cost) when types are known at compile time; `any`/interfaces only when they aren't.

---

## Concurrency

`std::thread` wraps native OS threads — no runtime, no safety checks.

```c3
Thread t;  t.create(&worker, arg)!!;  int code = t.join()!!;  t.detach()!!;
Mutex m;  m.init()!!;  m.lock()!!;  defer m.unlock();
m.@in_lock() { /* unlocked at block exit */ };

BufferedChannel{int}* ch = channel::create_buffered(mem, size: 16)!!;
ch.push(42)!!;  int v = ch.pop()!!;
```

Channels: `BufferedChannel` (ring), `UnbufferedChannel` (one in-flight), `UnboundedChannel` (growable), `OneShotChannel` (one value). Faults: `CHANNEL_CLOSED`, `CHANNEL_BLOCKED`, `CHANNEL_EMPTY`. `std::thread::ThreadPool` is the dynamic pool; `std::thread::pool::ThreadPoolOld{SIZE}` and `FixedThreadPool` are deprecated.

---

## Modules

```c3
module myapp::net::http;

fn void pub_fn()  @public {}   // default
fn void priv_fn() @private {}  // module-only
fn void file_fn() @local {}    // file-only, cannot be overridden

attrmacro @Hot = @inline, @export;
```

**Imports are recursive** (`import mylib` includes `mylib::net`, etc). Use `@norecurse` to opt out.

**Asymmetry:** types don't need a module prefix when unambiguous; functions always do.

---

## Compile-Time

```c3
// Top-level declarations: use @feat, NOT $if — $if/$endif cannot wrap a global declaration
fn void init() @feat(WIN32) { }
fn void init() @feat(!WIN32) { }

// $if is for statements inside a function body ($else takes NO colon)
fn void setup() {
    $if env::WIN32:
        io::printn("win");
    $else
        io::printn("other");
    $endif
}

char[] data = $embed("assets/shader.glsl");
```

`$else` takes **no** colon (`$if cond:` … `$else` … `$endif`). There is no else-if chain — `$elseif`, `$elif`, and `$else if` are all invalid. Nest a second `$if` inside `$else`, or use `$switch:` / `$case cond:` / `$default:` / `$endswitch` for multi-way branching.

Key builtins: `$Typeof(expr)`, `$Typefrom(id)`, `$defined(expr)`, `$assert(cond)`, `Type::size` / `::alignment` / `::kind`, `@sizeof(expr)`, `$reflect(field).name`, `$eval("name")`, `$expand("expr")`, `$feat(F)`. Use `&&&` and `|||` when a compile-time condition must skip type-checking its right-hand side.

Compile-time field access uses `a.$field` to read and `a.$field = b` to write (`a.$eval($field)` is an equivalent variant). The older `$field.get(a)` / `$field.set(a, b)` forms are deprecated as of 0.8.1.

Conditional compilation of a top-level declaration or module section uses `@feat(FLAG)`. Feature lists accept `&`, `|`, `!`, and parentheses; commas mean `|`, and repeated `@feat` attributes mean `&`. `$feat` accepts the same feature-list syntax. `@if` is restricted to generic declarations instantiated from generic parameters.

See `references/advanced.md` for macros, generics, interfaces, and operator overloading.

---

## Build

```bash
c3c init myproject
c3c run                      # build & run debug
c3c build release
c3c compile-run file.c3      # quick snippet test
c3c compile-only file.c3     # check without linking
c3c test [target]
c3c benchmark [target]
c3c source-lib src/lib.c3 -o my_lib
c3c fetch <library>
c3c project fetch [library ...]
c3c vendor-fetch <library>
c3c docgen
```

`project.json` targets support `"type": "executable" | "static-lib" | "dynamic-lib" | "source-lib" | "object-files" | "prepare" | "benchmark" | "test"`, `"depends-on"`, `"safe"`, `"opt"`, and `"strip-unused"`. Other useful 0.8.6 settings include `"features"`, `"function-sections"`, `"data-sections"`, `"stack-probe"`, `"stack-protector"`, `"env"`, and `"env-override"`. See `references/build-and-dependencies.md` for packaging and dependency rules.

Verify a snippet with `c3c compile-run snippet.c3`. Add `--use-stdlib=no` for stdlib-free examples. Enable `--warn-unusedlocal` and `--warn-unusedparam` for a stricter review. Use `--stats=summary`, `full`, or `json` for compiler statistics.

---

## Testing

```c3
fn void test_add() @test { assert(add(1, 2) == 3); }
fn void bench_add() @benchmark { for (int i = 0; i < 1000; i++) add(i, i+1); }
```

Run with `c3c test [target]` or `c3c benchmark [target]`. `std::core::test` provides `test::eq`, `test::@check`, and `test::@error` for richer assertions.

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
| Works in debug, misbehaves in release | Safe builds trap on UB; fast builds don't — test `c3c run` *and* `c3c build release` |
| `else if (x) foo();` rejected | Put the single statement in braces: `else if (x) { foo(); }` |
| Duplicate designated initializer | `{ .a = 1, .a = 1 }` is an error |
| `ulong x = -1` accepted before | Negative constants cannot implicitly convert to wider unsigned types |
| Same-size signed/unsigned aggregate cast | Casts between `int[3]`/`uint[3]`, slices, and vectors now require explicit casts |
| Old `attrdef` / `faultdef` spellings | Prefer `attrmacro` / `excuse` in current code |
| Empty infinite loop never panics | Detection is opt-in: `--infinite-loop-detect=yes`, safe mode only |
| Assuming `pool::ThreadPool` is current | Use `std::thread::ThreadPool`; `pool::ThreadPoolOld{SIZE}` is the deprecated fixed-capacity type |
