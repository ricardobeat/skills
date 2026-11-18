# C3: Complete Reference

---

## Contents

1. [Philosophy & Cost Model](#1-philosophy--cost-model)
2. [Naming Conventions](#2-naming-conventions)
3. [Memory & Ownership](#3-memory--ownership)
4. [Type System](#4-type-system)
5. [Methods, Interfaces & Dynamic Dispatch](#5-methods-interfaces--dynamic-dispatch)
6. [Error Handling — Optionals](#6-error-handling--optionals)
7. [Arrays, Slices & Array Combinators](#7-arrays-slices--array-combinators)
8. [Vectors (SIMD)](#8-vectors-simd)
9. [Generics](#9-generics)
10. [Macros & Compile-Time Execution](#10-macros--compile-time-execution)
11. [Concurrency](#11-concurrency)
12. [Standard Library](#12-standard-library)
13. [Testing](#13-testing)
14. [API Design Patterns](#14-api-design-patterns)
15. [Attributes Reference](#15-attributes-reference)

---

## 1. Philosophy & Cost Model

C3's core proposition: an evolution of C, not a revolution — the same paradigms, the same manual memory model, the same ABI, with the rough edges filed off. No garbage collector, no hidden allocations, no borrow checker. Every allocation is a function call you can see.

**Design goals, stated by the language itself:** procedural, pragmatic, minimalistic — no feature should be unnecessary or redundant. Stay close to C; only change where there is significant need. Seamless C integration. Ergonomic common patterns. Data is inert. Avoid "big ideas."

**Zero Is Initialization (ZII):** the load-bearing idiom of the whole language. Types and code are written so the zero value is a meaningful, initialized state — a zeroed `File*` is null, a zeroed `List` is an empty, usable list, a zeroed `HashMap` will lazily initialize itself on first `set`. This is why local variables zero-initialize by default (see below) and why so many container types work correctly with no explicit `init` call at all. Not every container gets this: `SortedMap` is declared `@mustinit` — a zeroed `SortedMap` is not a valid empty map, and using one before `.init()` is a bug, not a lazily-resolved convenience. Check a container's own doc comment before assuming ZII applies to it.

**Full C ABI compatibility:** C3 and C can call each other with zero glue code. `extern fn` on the C3 side, plain declarations on the C side. This is not FFI in the usual sense — there is no marshalling layer, no bindgen step required for a working build. A C3 struct has the same layout rules as a C struct unless you opt into `@packed` or `@compact`.

```c3
int a = 5;                          // stack — free
int[100] arr;                       // stack, zero-initialized by default — free
double[] slice = &arr;              // slice: {ptr, len} struct — free, no allocation
int* p = malloc(int::size);         // heap alloc — explicit, visible
int* p2 = mem::new(int);            // heap alloc, zero-initialized — same cost, clearer intent
int* p3 = tmalloc(int::size);       // temp-allocator alloc — freed in bulk at @pool() exit
Foo* f = mem::tnew(Foo);            // same, using the temp allocator
DString s;                          // dynamic string builder — lazily allocates on first append
List{int} list;                     // dynamic array — lazily allocates on first push
// Struct copies are bitwise memcpy, always — arrays are VALUES in C3, not pointers:
int[3] a = {1,2,3};
int[3] b = a;                        // full copy, not a view
// Function calls, method dispatch on non-interface types: direct call, zero overhead
// Generic instantiation: monomorphized per parameterization — zero overhead, like a
// preprocessor macro that's actually type-checked
// any / interface dispatch: one typeid comparison plus an indirect call, comparable
// cost to a C function pointer call
```

### Zero-Initialization by Default

Unlike C, local variables are zero-initialized unless you opt out:

```c3
int x;               // x = 0
int y @noinit;        // y is explicitly undefined; must be assigned before use
AStruct foo;          // foo is implicitly zeroed
AStruct bar = {};     // bar is explicitly zeroed (same result, different spelling)
AStruct baz @noinit;  // baz is explicitly undefined
```

Reading an `@noinit` variable before assignment traps in safe builds and is undefined behavior in fast builds. This trades a small, provably-eliminable store for a whole class of uninitialized-read vulnerabilities; `@noinit` exists for the rare case where the zeroing store is measurable and the variable is about to be fully overwritten anyway (e.g. right before a `read()` call).

### Undefined Behavior and Safe vs. Fast Builds

C3 has real undefined behavior, same as C — the compiler assumes it cannot occur and optimizes accordingly. The difference from C is what happens when it does occur. **Safe builds trap**: they insert a runtime check and abort with a trace, comparable to compiling C with a UB sanitizer permanently on. **Fast (release) builds** drop the checks and the UB is real UB — the compiler is free to assume it never happens.

```c3
uint x = foo();
uint z = 255 / x;
return x != 0;
// Safe build compiles roughly to:
//   uint x = foo();
//   if (x == 0) trap("Division by zero");
//   return true;
// Fast build compiles roughly to:
//   foo();
//   return true;          // compiler assumes x != 0, since x == 0 is UB
```

| Operation | Traps in safe builds |
|---|---|
| `int / 0`, `int % 0` | Yes |
| array index out of bounds | Yes |
| dereferencing `null` | Yes |
| violating `@require`/`@ensure` (contracts) | Yes |
| violating `assert()` | Yes |
| reaching `unreachable()` | Yes |
| reading explicitly-`@noinit` memory before assignment | Implementation-dependent |
| dereferencing freed or out-of-lifetime memory | Implementation-dependent |
| casting a pointer to an incompatible array type | Implementation-dependent |

Two things C leaves undefined that C3 defines: **signed integer overflow always wraps** (two's complement, same as unsigned), and modifying the intermediate result of an expression behaves as if that intermediate were stored in a stack variable first. Neither is a trap-worthy condition — they're just specified where C shrugs.

### Integers and Casting

```c3
// Signed: ichar, short, int, long, int128, iptr, sz
// Unsigned: char, ushort, uint, ulong, uint128, uptr, usz
// iptr/uptr match void* width; sz/usz match the max pointer-difference width.
// On 64-bit targets these usually coincide with long/ulong; on 32-bit, with int/uint.
```

C3 deliberately does **not** have per-operation `checked_add`/`wrapping_add`/`saturating_add`-style combinators on integers. The tradeoffs are handled at a coarser grain instead: signed overflow always wraps (defined behavior, not a trap), and narrowing casts are always silent — casting `300` to `char` truncates to `44` with no warning, in debug or release alike, exactly like C. If you need saturating or checked arithmetic, you write it, or reach for a vendor library; it is not baked into the primitive types. The compiler does expose the underlying overflow-detection machinery as `$$overflow_add`, `$$overflow_sub`, and `$$overflow_mul` builtins (each yielding a value plus an overflow flag, backed directly by the LLVM overflow intrinsics), but these are compiler builtins reached through `$$`, not ordinary methods callable as `x.checked_add(y)`.

### Cross-Module Inlining

```c3
fn int add(int a, int b) @inline { return a + b; }   // suggest inlining across module boundaries
```

There is a single `@inline` attribute, usable on a function declaration (suggest inlining) or on a specific call site (`foo() @inline;`, force this call to be inlined). There is no separate "always" vs "never" tier splitting a soft inline hint from a hard one; `@noinline` covers the opposite end, preventing a function or a specific call from being inlined.

**Idiomatic defaults:**
- Prefer `String` / slices (`Type[]`) over raw pointer + length pairs in function parameters — slices are bounds-checked in safe mode, plain pointers are not
- Prefer free functions over methods when a function is not primarily *about* one particular value — `io::fprintf(file, ...)` over `file.fprintf(...)`; see §14
- Reach for the temp allocator (`tmem`, `@pool()`) for anything scoped to a function call or a request; reach for `mem` (the heap allocator) for anything that must outlive the current scope
- `!!` force-unwrap is fine in `main()`, tests, and genuinely-impossible-to-fail paths; anywhere else, handle the `Optional` explicitly
- `@inline` every small, hot, cross-module-called function in a library
- Use `Allocator`-parameterized functions (`allocator::new`, `list::init(allocator)`) rather than hardcoding `mem` inside library code, so callers can supply their own arena

---

## 2. Naming Conventions

C3's naming rules are not a style guide — they are enforced by the **lexer**, not the semantic analyzer, because the grammar needs them to disambiguate a type name from a variable name with only one token of lookahead. There is no way to relax them; doing so would require an entirely different declaration syntax, which the language deliberately avoided. As the language's own FAQ puts it: either C3 keeps `int a = 2;` under these rules, or it needs an alternative declaration syntax altogether — and once that door opens, struct declarations, for-statements, and everything else built on the same grammar changes too, at which point nobody would recognize it as a C evolution anymore.

```c3
// User-defined types (struct, union, enum, typedef, alias, fault, interface):
// must start with A–Z after an optional leading underscore, and contain at
// least one lowercase letter. `Bar`, `_T_i12`, `TTi` are valid; `_1`, `bAR`,
// `BAR` are not.
struct Foo { ... }
enum Baz { VALUE_1, VALUE_2 }

// Variables and parameters: must start with a–z after an optional leading
// underscore. `___a`, `fooBar`, `_test_` are valid; `_`, `_Bar`, `X` are not.
int the_global = 1;
fn void foo(int x) { ... }

// Global constants: must start with A–Z after an optional leading underscore.
const int A_VALUE = 12;

// Enum members and faults (faultdef) follow the SAME rule as global constants.
enum Baz { VALUE_1, VALUE_2 }
faultdef OOPS, LOTS_OF_OOPS;

// Modules: lowercase letters, digits, underscore only. No uppercase.
module foo::bar::baz;

// Functions and macros: must start with a–z after an optional leading underscore.
fn int another_function() { ... }
macro just_do_it(x) { ... }
```

All identifiers: `a-z A-Z 0-9 _`, no leading digit, max 127 characters. Module sub-paths max 31 characters; a full module path max 63.

### The Standard Library Convention

The language itself doesn't mandate a *style* — only the *casing rule per category* above is enforced. But the standard library, and anything meant to look native alongside it, follows one further convention on top:

```c3
alias MyInt = int;      // Types: PascalCase
struct SomeStructType
{
    int a_field;         // Members: snake_case
    double foo_baz;
}
int some_global = 1;     // Globals: snake_case
fn void some_function(int a_param)  // Functions and parameters: snake_case
{
    int foo_bar = 4;     // Locals: snake_case
}
// Methods: snake_case; first parameter is conventionally (not compiler-enforced) "self"
fn void SomeStructType.call_me(self, int a)
{
    some_function(self.a_field + a);
}
macro @some_macro(a) { return a + a; }  // Macros: snake_case
const MY_FOO = 123;      // Constants: SCREAMING_SNAKE_CASE
```

Summary: **types PascalCase, constants SCREAMING_SNAKE_CASE, everything else snake_case.** The stdlib uses Allman brace style; outside the stdlib, either Allman or K&R is acceptable, and contributions elsewhere are not required to match. Contributions to the stdlib itself use tabs for indentation.

### Why `::` and Not `.` for Namespacing

`.` is used exclusively for member/method access; `::` is used exclusively for module-qualified names. This isn't cosmetic — it's what makes "path shortening" possible: `file::open(...)` works without writing `std::io::file::open(...)` because the compiler can tell, purely from the `::`, that `file` names a module and not a local variable, even before it has resolved anything. If `.` served both roles, `file.open(...)` would be ambiguous whenever a local variable named `file` was also in scope.

### Type Declaration Order Reads Inside-Out

C3 deliberately inverts C's declarator syntax: the innermost part of a type is written leftmost, and dereferencing/indexing peels off the *rightmost* layer first.

```c3
int[4]*        // pointer to an array of 4 ints — read "array of 4 int, then pointer to that"
int*[4]*       // pointer to an array of 4 (pointer to int)
List{int}[3] x;  // array of 3 List{int} — x[1] is a List{int}; x[1][5] indexes into that list
```

This is the reverse of C's `int (*foo)[4]`-style declarators, where you have to mentally unwind from the variable name outward. C places `*` and `[]` on the *variable*, in the order it must be unpacked — so `int (*foo)[4]` dereferences first (giving `int[4]`), then indexes. Pulled out as a standalone type, that's `int(*)[4]`, a pointer to an array of 4 ints — and once arrays of pointers enter the picture, C's spelling gets markedly harder to read (`int*(*)[4]`, a pointer to an array of 4 int pointers) than C3's `int*[4]*`, because C's declarator syntax makes you track which of `*` or `[]` binds tighter. The tradeoff C3 makes: this syntax is unambiguous and left-to-right readable for arbitrarily nested pointer/array combinations, at the cost of not looking like C once you nest deeply.

---

## 3. Memory & Ownership

There is no borrow checker, no ownership tracking, no lifetimes. Memory is manually managed, same as C — the improvements are in *what the standard library gives you to make manual management less error-prone*, not in taking manual management away.

### Stack vs. Heap

```c3
fn void test()
{
    int a = 12;      // stack
    int b = a;       // copies the value — plain assignment, not a move
    int[2] c = {1, 2};
    int[2] d = c;    // arrays are VALUES — this is a full copy
    io::printn(d);   // "{ 1, 2 }"
    c[0] = 10;
    io::printn(c);   // "{ 10, 2 }"
    io::printn(d);   // "{ 1, 2 }" — d is untouched, it was never aliased to c
}
```

There is no move semantics distinct from copy: assigning a struct or array copies it, always, bitwise. There is no distinct "non-copyable" type category — every value type behaves the same way on assignment. The only way to share mutable state between two names is a pointer.

### Allocating on the Heap

```c3
// Doesn't compile: can't return a slice into a stack-local array.
fn int[] create_array_bad(int n)
{
    int[100] arr;
    for (int i = 0; i < n; i++) arr[i] = i;
    return arr[:n];   // ERROR: returns a pointer to a stack-allocated variable
}

// Correct: allocate on the heap, return a slice over the allocation.
<* @require n >= 0 *>
fn int[] create_array(int n)
{
    int* arr = malloc(n * int::size);
    for (int i = 0; i < n; i++) arr[i] = i;
    return arr[:n];       // turn the pointer into a {ptr, len} slice
}

fn void test()
{
    int[] array = create_array(3);
    do_things(array);
    free(array);          // release back to the OS — slices free just like pointers
}
```

Prefer the convenience wrappers over raw `malloc`/`calloc` — they're clearer about intent and equally cheap:

```c3
Foo* f1 = malloc(Foo::size);                      // uninitialized
Foo* f2 = calloc(Foo::size);                      // zero-initialized
Foo* f3 = mem::new(Foo);                          // zero-initialized, same as calloc
Foo* f4 = mem::alloc(Foo);                        // uninitialized, same as malloc
Foo* f5 = mem::new(Foo, { 4, 10.0, .a = 123 });   // zero-init then apply an initializer in one call

Foo[] arr1 = mem::new_array(Foo, 10);   // zero-initialized array, as a slice
Foo[] arr2 = mem::alloc_array(Foo, 10); // uninitialized array, as a slice

int* x = @clone(33);           // heap-allocate a copy of a value
int[] a = @clone_slice(z);     // heap-allocate a copy of a slice/array's elements
```

There are also `new_with_padding` (allocate extra trailing bytes past a struct's own size — used by variable-length-tail types) and `new_aligned` (for overaligned types, typically SIMD vectors with alignment greater than 16), for the less common cases `new`/`alloc` don't cover.

### The Temp Allocator — Bulk-Freed Scratch Memory

The temp allocator is C3's answer to "I need this for the rest of this function call tree and then I want it gone, all at once, with no bookkeeping." It's a stack/arena allocator: allocate freely with `tmalloc`, `tcalloc`, `mem::tnew`, `mem::temp_array`, and so on; there is **no `free` for individual temp allocations**. Instead, you wrap a scope in `@pool()`, and everything allocated on the temp allocator anywhere inside that scope — including in functions called from inside it — is released in one shot when the scope exits.

```c3
fn void some_function()
{
    @pool()
    {
        do_calculations();   // anything it tmallocs is cleaned up below
    };
    // All temporary allocations inside do_calculations, and deeper, are
    // freed here, when the @pool scope exits.
}

// Single-expression function body syntax composes with @pool cleanly:
fn void a_function() => @pool()
{
    test_temp();
    void* data = tmalloc(1000);
}
```

`@pool()` scopes nest correctly — an inner pool's allocations are released at the inner pool's exit; the outer pool's allocations survive until the outer exit:

```c3
fn void nested()
{
    @pool()
    {
        int* a = tmalloc(int::size);
        *a = 123;
        @pool()
        {
            int* b = tmalloc(int::size);
            *b = *a;          // both a and b valid here
        };
        // b is released; a is still valid
        io::printn(*a);
    };
    // a is released
}
```

**The one real footgun:** never let temp-allocated data outlive its `@pool()` scope — don't hand it to another thread, don't stash it in a variable that escapes the scope, don't return it from the function that owns the pool without an explicit workaround (below). The compiler's ability to catch this depends on safety-checking / address-sanitizer settings, and support differs across OS and architecture; it is not guaranteed to be caught.

```c3
// To return something built with the temp allocator, capture the allocator
// value BEFORE entering @pool, and allocate the thing you're keeping through
// that captured copy explicitly — it will not be swept up by the inner @pool.
Allocator temp = tmem;
@pool()
{
    // Note: 'temp != tmem' here — tmem now refers to the INNER pool's allocator.
    void* scratch = tmalloc(128);            // swept when @pool exits
    Foo* foo = allocator::new(temp, Foo);    // allocated through the OUTER temp, survives
    foo.z = compute(scratch);
    return foo;
};
```

Because the temp-allocator idiom is so common, many stdlib functions have a `t`-prefixed or `temp_`-prefixed twin that uses it implicitly:

```c3
List{int} list;
list.tinit();                              // init on the temp allocator
String s = string::tformat("Hello %s", "World");  // format via the temp allocator
```

### Implicit Initialization and ZII in Containers

`List`, `HashMap`, `HashSet`, and `DString` all implicitly initialize themselves on the *temp* allocator the first time you use them, if you never call `init`/`tinit` explicitly. This is Zero Is Initialization in action — a zeroed container is a valid, usable, empty container:

```c3
@pool()
{
    List{int} list;
    list.push(1);     // implicitly initialized on tmem here
    list.push(42);

    DString str;                       // zero-valued DString
    str.appendf("Hello %s", "World");  // implicitly initialized here too
    str.insert_at(5, ",");
    str.append("!");
    io::printn(str);                   // "Hello, World!"
};  // list and str both freed here, as part of the pool
```

`SortedMap` is the exception: it's declared `@mustinit`, so a zeroed `SortedMap` is not a valid empty map the way a zeroed `List` is — call `.init()` before using one.

For a **global**, implicit-temp-allocator behavior is almost always wrong — a global outlives any `@pool()`. `List`, `HashMap`, and `HashSet` each expose an `ONHEAP` constant for exactly this. `SortedMap` also has an `ONHEAP` of its own. The ordered/insertion-preserving variants use a differently-named constant — `OrderedMap`/`OrderedSet` expose `ORDEREDONHEAP` rather than `ONHEAP` — so check the specific container's declaration rather than assuming the name carries over:

```c3
List{int} l = list::ONHEAP{int};
fn void main()
{
    l.push(1);   // allocates on the heap allocator, not tmem
}
```

`DString` has no `ONHEAP` equivalent at all — a global `DString` can only be pointed at the heap allocator by calling `.init(mem)` at runtime, typically from a static initializer (`@init`, see §14).

### Functions That Allocate Take an `Allocator`

Standard library functions that allocate generally take the allocator as an explicit parameter, rather than hardcoding a global heap. `mem` is the process heap allocator; `tmem` is the temp allocator; either can be passed anywhere an `Allocator` is expected, and so can your own arena implementation:

```c3
List{int} list;
list.init(mem);     // uses the heap allocator
list.push(1);
list.push(42);
list.free();         // must free manually — mem-backed containers don't self-clean

String s = string::format(mem, "Hello %s", "World");   // heap-allocated
io::printn(s);
free(s);
```

### `defer` — Deterministic Scope-Exit Cleanup

`defer` is C3's mechanism for "run this when the current scope ends, no matter how it ends" — there is no automatic destructor call anywhere in C3; if a type needs cleanup, that cleanup happens because *someone wrote a `defer`*, not because the compiler inserted one.

```c3
fn void test(int x)
{
    defer io::printn();
    defer io::print("A");
    if (x == 1) return;
    {
        defer io::print("B");
        if (x == 0) return;
    }
    io::print("!");
}
fn void main()
{
    test(1);   // prints "A"
    test(0);   // prints "BA"
    test(10);  // prints "B!A"
}
```

**Multiple `defer`s in the same scope run in reverse declaration order** — last declared, first run:

```c3
fn void test()
{
    io::printn("first");
    defer io::printn("third — runs last, declared first");
    defer io::printn("second — runs first, declared last");
}
```

`defer` only fires for scope exits *after* the point it's declared — if the function returns before reaching the `defer` statement, that `defer` never runs. This is a feature, not a footgun: it means you write the cleanup right after acquiring the resource, and anything that fails to acquire never triggers a cleanup for a resource it never held.

```c3
fn char[]? file_read(String filename, char[] buffer)
{
    File file = file::open(filename, "r")!;   // if this fails, no file to close — correct
    defer (void)file.close();                  // only registered AFTER a successful open
    file.read(buffer)!;
    return buffer;
}
```

**`defer try` / `defer catch`** split cleanup by whether the function is exiting with a value or exiting with a fault (see §6) — invaluable for "only log on the error path" or "only flush on the success path":

```c3
fn void? test(int x)
{
    defer io::printn("");
    defer io::print("A");
    defer try io::print("X");         // only runs if the scope exits with a RESULT
    defer catch io::print("B");       // only runs if the scope exits with a FAULT
    defer (catch err) io::printf("%s", err);   // like `catch`, but captures the fault value
    if (x == 1) return NOT_FOUND~;
    io::print("!");
}
```

Declare `defer`/`defer catch` **as close to the resource acquisition as possible** — anything that can rethrow (`!`) between the acquisition and the `defer` will skip the cleanup entirely, because the `defer` hasn't been registered yet:

```c3
fn String? test()
{
    char[] data = mem::new_array(char, 12);

    // ❌ If function_throws()! fires here, `data` leaks — the defer below
    // hasn't executed yet, because the compiler hasn't even reached it.
    // function_throws()!;

    defer (catch err) { io::printn("freeing memory"); free(data); }

    // ✅ After the defer is registered, any rethrow past this point is safe.
    function_throws()!;

    return (String)data;
}
```

### `Guard`-Shaped Types — the RAII Pattern, Written by Hand

Because there is no automatic destructor, the "acquire in constructor, release in destructor" pattern is instead: write a small struct, and pair every instance with a `defer` at the point of acquisition.

```c3
struct LockGuard { Mutex* mutex; }
fn LockGuard acquire(Mutex* m) { m.lock(); return { m }; }
fn void LockGuard.release(&self) { self.mutex.unlock(); }

fn void critical_section(Mutex* m)
{
    LockGuard guard = acquire(m);
    defer guard.release();
    // ... protected work ...
}
```

The standard library's own `@in_lock` macro packages exactly this pattern for `Mutex` — it's a two-line macro built on the same `defer` primitive, not special compiler magic:

```c3
macro void Mutex.@in_lock(&mutex; @body)
{
    mutex.lock();
    defer mutex.unlock();
    @body();
}
```

```c3
m.@in_lock()
{
    // protected work; the mutex is released automatically at the end
    // of this block via an internal defer, even on early return
};
```

Nothing in the type system stops you from copying a `Guard`-shaped struct and calling `release()` twice — there's no exclusivity rule to lean on. The convention (see §14) is: guard types are never given value-semantics that make sense to copy, and disciplined code simply doesn't clone them.

---

## 4. Type System

### Structs

```c3
struct Person
{
    char age;
    String name;
}

fn void test()
{
    Person p;
    p.age = 21;
    p.name = "John Doe";
    io::printfn("%s is %d years old.", p.name, p.age);

    Person* p_ptr = &p;
    p_ptr.age = 20;    // dot access works through one level of pointer automatically
}
```

**Initialization:**

```c3
Person p = { 21, "John Doe" };                    // positional
Person p2 = { .age = 21, .name = "John Doe" };     // designated — order-independent
Person p3 = { .name = "John Doe" };                // omitted fields zero — p3.age == 0

// Splatting: take an existing value as defaults, override specific fields
Person p4 = { ...p, .age = 22 };   // same as { 22, "John Doe" }
```

**Struct subtyping via `inline`:**

```c3
struct ImportantPerson
{
    inline Person person;   // ImportantPerson "is-a" Person for the purposes below
    String title;
}

fn void print_person(Person p) { io::printfn("%s is %d.", p.name, p.age); }

fn void test()
{
    ImportantPerson vip;
    vip.age = 25;             // fields of the inlined struct are promoted — no vip.person.age needed
    vip.name = "Jane Doe";
    vip.title = "Rockstar";
    print_person(vip);        // implicit slice: only the Person-shaped prefix is passed
}
```

`inline` is also how a type picks up dynamic-interface methods from an embedded "parent" (see §5) and how a `typedef` can implicitly convert *to* its underlying type without converting back (see §14's `Params`/`Settings` discussion).

### Unions

```c3
union Integral { char as_byte; short as_short; int as_int; long as_long; }
// Fully C-ABI compatible. Only one member is "active" at a time; reading a
// member other than the last one written is undefined behavior — same rule as C.
// Integral::size == long::size: a union is sized to its largest member.
```

Anonymous and named sub-structs/sub-unions nest inside a struct the same way they do in C99+:

```c3
struct Person
{
    char age;
    String name;
    union { int employee_nr; uint other_nr; }         // anonymous — access as p.employee_nr
    union subname { bool b; Callback cb; }              // named — access as p.subname.b
}
```

### Layout Control

Plain C3 structs and unions already share C's layout rules by default, which is one of the load-bearing pieces of "full ABI compatibility." The attributes below adjust *away* from that default:

```c3
struct Foo @align(32)              // minimum alignment; can only INCREASE, never decrease
{
    int a;
    int b @align(16);
}
struct Bar @packed { ... }         // every member alignment forced to 1
struct Baz @compact { ... }        // like @packed, but recursive into sub-elements too — no
                                    // padding ANYWHERE in the tree, not just at the top level
struct Quux @nopadding { ... }     // compile ERROR if any padding would be needed, rather than
                                    // silently removing it
```

To shrink below the default alignment, `@packed` first (alignment 1 everywhere), then `@align` back up to the value you actually want.

### `const` vs. Compile-Time Folding

```c3
const int MAX = 100;              // compile-time constant, folded at every use site
const MY_FOO = 123;                // type inferred
```

There is no separate category of compile-time-evaluable functions distinct from ordinary ones. Instead, compile-time execution lives entirely in **macros** with `$`-prefixed (compile-time) parameters — a macro whose parameters are all `$`-prefixed and whose body only returns is fully constant-folded wherever it's called with constant arguments (see §10). `const` itself just marks a *value* as a compile-time constant; it doesn't make a function body compile-time-executable.

C3 also removed C's `const` type-qualifier and `volatile` type-qualifier entirely — there is no `const int*` distinct from `int*` at the type level. `const` in C3 is a *storage class* modifier for declaring compile-time constant values, not a type qualifier describing a read-only *view* of a pointer; per the language's own FAQ, "const correctness" was judged to add pervasive noise for guarantees weaker than they look. In place of `volatile`, the standard library provides `@volatile_load`/`@volatile_store` macros that do the same job explicitly, at the call site, rather than baking it into a type:

```c3
// Both loads always happen — the compiler can't elide or reorder past a volatile op:
int y = @volatile_load(my_global);
y = @volatile_load(my_global);
@volatile_store(y, 1);
```

Restrictions on what a function may do to its pointer parameters — the closest analog to C's `const` on a parameter — are instead expressed as parameter-direction contracts (`@param [in]`, see §10), which the compiler checks and can partially enforce, rather than as a type qualifier.

### Enums as Namespaced, Associated-Value Sum Types

```c3
enum State : int { WAITING, RUNNING, TERMINATED }
State current = WAITING;    // or State.WAITING — both work when the type is inferable
```

Enums are **always namespaced** (`State.WAITING`, like a C++ scoped enum, not a C enum) — plain `WAITING` only resolves when the surrounding context already pins down the type, e.g. a `switch` on a `State` or a variable declared `State`.

Enum values can carry **associated static data**, declared once per enum as a typed field list, then populated per-variant:

```c3
enum State : int (String label, bool active)
{
    WAITING    { "waiting", false },
    RUNNING    { "running", true  },
    TERMINATED { "ended",   false },
}
fn void main()
{
    State process = RUNNING;
    if (process.active) io::printfn("Process is: %s", process.label);
}
```

This is structurally different from a payload-carrying tagged union: every variant of a given enum shares the *same* associated-field schema (here, every `State` has a `label` and an `active`), rather than each variant defining its own independent shape. There is no tagged-union type in C3 at the time of writing — the design space for one is still under discussion upstream.

```c3
process.ordinal              // 1 (index into declaration order)
State::from_ordinal(1)       // RUNNING — round-trips
(int)process                 // plain cast also works
State::values                // [WAITING, RUNNING, TERMINATED]
State::names                 // ["WAITING", "RUNNING", "TERMINATED"]
State::len                    // 3
State::lookup_field(label, "running")   // finds RUNNING by its associated value
```

Every switch over an enum without a `default:` is checked for exhaustiveness by the compiler, and adding a variant later is a genuine breaking change for downstream exhaustive switches, by design.

### `constdef` — Non-Sequential C-Style Enums

Standard `enum` values are always sequential ordinals starting at zero — this is enforced. When interfacing with a C enum that has gaps or specific numeric values, use `constdef` instead, which behaves like an `alias` over the backing type rather than a true enum:

```c3
constdef KeyCode
{
    UNKNOWN   = 0,
    RETURN    = 13,
    ESCAPE    = 27,
    BACKSPACE = 8,
    SPACE     = 32,
    EXCLAIM,           // auto-incremented to 33
}
fn void main()
{
    int a = (int)KeyCode.SPACE;     // 32
    KeyCode b = (KeyCode)2;          // valid even though 2 isn't declared — constdef doesn't
                                      // enforce that every value maps to a name
    KeyCode key = get_key_code();    // safe to receive directly from a C function
}
```

### `fault` — Typed Error Tags

`fault` is the type of an error tag in C3's `Optional` model (§6) — a named, small, comparable value, roughly analogous to an error-code enum but without ordinal semantics:

```c3
faultdef DIVISION_BY_ZERO;
faultdef DOG_ATE_HOMEWORK, TEXTBOOK_ON_FIRE;   // multiple in one declaration
```

`fault` values follow the same naming rule as global constants (SCREAMING_SNAKE_CASE, capital-letter start). See §6 for how they're returned, matched, and chained.

### Generics as Monomorphization

```c3
module stack <Type>;   // parameterized module — everything declared inside is generic over Type

struct Stack { sz capacity; sz size; Type* elems; }

fn void Stack.push(&self, Type element)
{
    if (self.capacity == self.size)
    {
        self.capacity = self.capacity ? self.capacity * 2 : 16;
        self.elems = realloc(self.elems, Type::size * self.capacity);
    }
    self.elems[self.size++] = element;
}
fn Type Stack.pop(&self) { assert(self.size > 0); return self.elems[--self.size]; }
```

```c3
alias IntStack = Stack{int};
alias DoubleStack = Stack{double};

fn void test()
{
    IntStack s;          // fully separate, monomorphized instantiation — no vtables, no
    s.push(1);            // boxing, no shared code between IntStack and DoubleStack; this
    s.push(2);             // is generated code, same cost model as if you'd hand-written
                             // two separate Stack_int / Stack_double structs
    io::printfn("pop: %d", s.pop());  // 2
}
```

Note the split: `<Type>` marks the parameter at the **declaration** site (on the `module` line, or on an individual `struct`/`fn`); `{Type}` supplies the concrete parameter at the **instantiation** site (`Stack{int}`, `List{String}`). Mixing these up — writing `struct Stack{Type}` where a declaration is meant — is a common transcription error; the stdlib itself consistently writes `module std::collections::list <Type>;` for declarations and reserves the curly-brace form for use sites.

Every distinct set of type parameters used anywhere in a program gets its own compiled instantiation — the zero-cost-abstraction story is the same one C++ templates tell, just without a first-class trait-bound syntax: constraints on what a generic parameter must support are expressed as **contracts** (`@require $defined(...)`, see §10), checked at instantiation time, rather than as a bounds clause on the declaration.

### Typestate Without a Marker Type

C3 has no need for a zero-sized, compile-time-only marker type to encode "this value is in state X" the way some ownership-tracking type systems do, because there is no borrow checker or drop-checker consuming that information in the first place — nothing in C3's generics reads a type parameter that is never actually stored, since a generic parameter must be genuinely used as a type somewhere in the struct or its methods to be meaningful in monomorphization. Typestate in C3 is more commonly expressed with `distinct` unit-marker structs passed as ordinary (non-generic) parameters, or simply with a runtime enum field plus contract-checked methods (`@require self.state == PENDING`).

### Every Type Has a Compile-Time-Known Size

C3 doesn't have an unsized-type split — every C3 type has a compile-time-known size. There is no type usable without indirection the way an unsized type would be; a slice (`char[]`) is always a fixed-size `{ptr, len}` struct, and `any`/interface values (§5) are always passed as fixed-size fat pointers. Nothing in C3's type system requires a "relax the size bound" escape hatch, because nothing implicitly imposes one.

---

## 5. Methods, Interfaces & Dynamic Dispatch

### Methods Are Free Functions With a Namespace Prefix

A "method" in C3 is exactly a regular function whose first parameter's type gives it a namespace, letting you call it with dot syntax. There is no `impl` block, no vtable involved unless you explicitly ask for one (see Interfaces, below) — a method call on a concrete type compiles to a direct call, identical to calling the equivalent free function.

```c3
struct Foo { int i; }

fn void Foo.next(Foo* self) { if (self) self.i++; }

fn void test()
{
    Foo foo = { 2 };
    foo.next();
    foo.next();
    io::printfn("%d", foo.i);   // 4 — same as Foo.next(&foo); Foo.next(&foo);
}
```

Three equivalent-looking but distinct ways to spell the receiver:

```c3
fn int Foo.test(&self) { ... }         // shorthand — implies Foo* self, non-null
fn int Foo.test(Foo* self) { ... }     // spelled out — this form is required if you need
                                          // a NULLABLE receiver; &self always means non-null
fn int Bar.test(self) { ... }           // no & at all — receiver taken BY VALUE (a full copy)
```

You can add methods to types you didn't define, including built-ins:

```c3
fn int int.add(int self, int other) { return self + other; }
fn void test() { int i = 3; int j = i.add(4); }
```

**When to reach for a method vs. a free function** is a real, documented convention, not just taste: the standard library prefers free functions unless the function is fundamentally *about* one particular value's own state.

```c3
io::fprintf(file, "Hello %s", name);   // PREFERRED — extends easily to work with many types
file.fprintf("Hello %s", name);         // convention discourages this shape

foo.add(bar);       // GOOD method use — mutates or reads *this* value specifically
foo.to_list();       // GOOD
foo.push(x);          // GOOD
context.parse_data(data);   // DISCOURAGED — reads more like a free function pretending
game.run(settings);            //   to be a method; prefer task::run(game, settings) etc.
url.make_request();
```

There are **no static methods** and **no static (type-associated) variables** in C3, on purpose. As the language's own FAQ explains: static methods create a tension between free functions living in a module and functions namespaced by a type — some languages (Java, for instance) resolve this by not having free functions at all. C3 resolves it the other way: by not having static methods or static variables, so that anything which would be a static method elsewhere simply becomes a free function namespaced by the module instead.

### `any` — a Typed `void*`

`any` pairs a pointer with a runtime `typeid`, and is the mechanism for writing code that's polymorphic at runtime without going through generics or a formal interface. It is created implicitly by assigning any pointer to it:

```c3
fn void describe(any a)
{
    switch (a.type)
    {
        case Foo.typeid: io::printn("a Foo");
        case Bar:        io::printn("a Bar");  // ::typeid can be elided in a case
        default:         io::printn("something else");
    }
}
```

Because the runtime `typeid` carries full reflection information, you can inspect size, alignment, and members through it — `a.type.size`, `a.type.name`, and so on — without knowing the concrete type at the call site. This is enough to copy an `any`'s pointee without ever naming its concrete type:

```c3
void* data = malloc(a.type.size);
mem::copy(data, a.ptr, a.type.size);
any any_copy = any_make(data, a.type);
```

### Interfaces — Message-Passing Dynamic Dispatch

C3's interfaces are not vtables baked into the type at compile time; they're closer to Objective-C-style message passing, layered over `any`. A method must be explicitly marked `@dynamic` to be reachable through an interface at all — plain methods are never implicitly part of any interface's dispatch table.

```c3
interface MyName { fn String myname(); }   // note: no "self" parameter in the declaration

struct Baz (MyName) { int x; }              // declares that Baz implements MyName

fn String Baz.myname(Baz* self) @dynamic { return "I am Baz!"; }   // @dynamic is required
```

A type that declares an interface but doesn't implement all its methods is a compile-time error. A type can implement several interfaces: `struct Foo (VeryOptional, MyName) { ... }`. A limitation worth knowing: only user-defined types may formally declare that they implement an interface. Making an existing built-in type satisfy an interface (below) is possible, but skips the compile-time completeness check.

You can also mark a method `@dynamic` **without** the owning type formally declaring any interface — this makes the type satisfy any interface with a matching signature, ad hoc. This is real, idiomatic stdlib practice — it's exactly how `Uuid`, `ComplexNumber`, and `Url` all pick up the `Printable` interface's `to_format` without a `(Printable)` declaration in sight:

```c3
// This will make "int" satisfy the MyName interface
fn String int.myname(int*) @dynamic { return "I am int!"; }

// Real stdlib examples, all following the same ad hoc pattern:
fn sz? Uuid.to_format(&self, Formatter* formatter) @dynamic { ... }
fn sz? ComplexNumber.to_format(&self, Formatter* f) @dynamic { ... }
```

Note that real `@dynamic` implementations overwhelmingly use the `&self` shorthand for the receiver, exactly as an ordinary method would — the interface declaration itself omits a receiver entirely (interfaces describe a method signature, not a parameter list with a `self`), but the *implementation* names its receiver like any other method.

Calling through the interface, with a runtime existence check for optional methods:

```c3
fn void whoareyou(any a)
{
    MyName b = (MyName)a;
    if (!&b.myname) { io::printn("I don't know who I am."); return; }
    io::printn(b.myname());     // dynamic dispatch — resolved by typeid at runtime
}
```

Interface methods marked `@optional` need this existence check before calling; required interface methods do not, since the compiler already verified they exist at the point the type declared conformance.

**Subtype inheritance of dynamic methods:** a struct with an `inline` member (or a `typedef` declared `inline`) inherits its parent's `@dynamic` methods automatically. This inheritance is not available for `inline` enums:

```c3
struct BazChild { inline Baz b; int x; }
// any pointer to BazChild will resolve MyName.myname to Baz.myname automatically
```

### Cost Model: `any`/Interface Dispatch vs. Generic Monomorphization

Reach for **generics** (§4, §9) when the set of concrete types is known at compile time and you want zero runtime dispatch cost — this is the default, and should be the default. Reach for **`any`/interfaces** when the concrete type genuinely isn't known until runtime — plugin systems, heterogeneous containers, anything crossing a serialization or scripting boundary. The interface path costs a `typeid` comparison plus an indirect call per dispatch, comparable to (not dramatically worse than) a C function-pointer call; it is not "boxing" in the heap-allocation sense, since `any` is just a fat pointer to data that may already live on the stack or heap regardless.

---

## 6. Error Handling — Optionals

C3 does not have a two-generic-parameter result type carrying a distinct error type per call site. It has **Optionals**, and the distinction is deliberate, not cosmetic: a `T?` is a value that is either present, or *empty with an attached fault* — closer to a self-explaining "maybe" than to a value/error pair whose error type varies from call to call. The reasoning, straight from the language's own FAQ: two fallible functions that each carry their own distinct error type cannot trivially compose — you can't implicitly combine the result of one with the result of another when their error types differ — whereas an `Optional`'s fault is always the same underlying `fault` type, so chaining, flat-mapping, and short-circuiting all work uniformly regardless of what specific fault two different fallible calls might produce. The size of the fault is also fixed — pointer-sized — so an `Optional` never costs more than a nullable value or a boolean-flagged return would. The name itself is chosen deliberately: C3's Optional leans toward "maybe" semantics rather than toward a value/error pair, and the name nudges usage in that direction.

### The Shape

```c3
int? a = 1;                       // Optional holding a result
int? b = io::FILE_NOT_FOUND~;      // Optional holding a fault — `~` attaches the fault
```

`?` after a type makes it Optional. `~` after a `fault` value turns it into "the empty case of an Optional, carrying this fault."

### Unwrapping Safely: `if (catch)`

```c3
fn void? test() { return io::FILE_NOT_FOUND~; }

fn void main(String[] args)
{
    if (catch excuse = test())
    {
        io::printfn("test() gave a fault: %s", excuse);
    }
}
```

`if (catch excuse = optional_value)` runs its block only when the Optional is empty, binding the fault. Crucially: **if you exit the current scope from inside that block** — `return`, `break`, `continue`, or rethrow (`!`) — the compiler knows the Optional variable can no longer be empty past that point, and **automatically unwraps it to its plain, non-Optional type** for the rest of the enclosing scope:

```c3
fn void? test()
{
    int? foo = unreliable_function();
    if (catch excuse = foo) { return excuse~; }   // propagate the fault and return
    io::printfn("foo: %s", foo);    // foo is a plain `int` here, not `int?`, by flow typing
}
```

### The Rethrow Operator `!`

`expr!` is sugar for "unwrap `expr`, or immediately return its fault from the current function" — the enclosing function's return type must itself be Optional for this to typecheck (`fn void? test()`, not `fn void test()`).

```c3
fn int? maybe_function() { /* ... */ }

fn void? test()
{
    int bar = maybe_function()!;
    // Desugars to:
    //   int? temp = maybe_function();
    //   if (catch excuse = temp) return excuse~;
    //   int bar = temp;   // now unwrapped
}
```

### `??` — Default Value on Empty

```c3
int regular_value = foo_may_error() ?? -1;   // -1 if foo_may_error() is empty, else its result

// Also used to REPLACE the fault with a more specific one — very common for
// distinguishing two call sites that could otherwise produce the same fault:
int? c = test() ?? DOG_ATE_HOMEWORK~;
int? d = test() ?? TEXTBOOK_ON_FIRE~;

// Combine with rethrow to immediately propagate a remapped fault:
int e = test() ?? DOG_ATE_HOMEWORK~!;
```

### `if (try)` — the Positive-Space Twin of `if (catch)`

```c3
if (try optional_value)
{
    io::printfn("Result found: %s", optional_value);   // unwrapped inside this scope
}
if (try unwrapped = optional_value)
{
    io::printfn("Result found: %s", unwrapped);          // bound to a new name instead
}
```

`if (try)` conditions can be joined with `&&` (each subsequent `try` sees the earlier ones already unwrapped) but **not** with `||` — an `Optional`'s emptiness isn't something you can meaningfully "or" together the way boolean conditions can, since each side would need independent unwrapping semantics that don't compose.

### Force-Unwrap: `!!`

```c3
find_file()!!;   // panics (traps) if find_file() is empty; roughly:
                   // if (catch) unreachable("Unexpected fault");
```

Use sparingly, and mostly in `main()`, tests, or genuinely-impossible-to-fail internal invariants.

### Optionals Propagate Through Expressions and Call Arguments

Any expression touching an Optional becomes Optional itself; and a function call with Optional arguments only actually executes if **every** Optional argument holds a result — otherwise the call is skipped entirely and the **first** fault found, scanning left to right, becomes the result:

```c3
int? first = io::FILE_NOT_FOUND~;
int? second = 7;
int? third = test(first, second);   // test() never runs; third == io::FILE_NOT_FOUND
```

This is why an Optional-returning call used purely for side effects (like a `printfn`) has to be explicitly discarded with a `(void)` cast if you don't want the compiler flagging an ignored Optional:

```c3
(void)io::printfn("%d", test_error());   // explicitly acknowledge we're ignoring the Optional
```

### Getting the Fault Without Unwrapping

```c3
fault excuse = @catch(optional_value);    // never triggers auto-unwrap, unlike if(catch)
bool has_result = @ok(optional_value);     // == !@catch(optional_value)
```

`@catch` is the only legal way to extract the fault from a `void?`-returning call without going through `if (catch)`, since `void?` itself cannot be stored in a variable — see below.

### `void?` Has No Variable Form

```c3
fn void? test() { return io::FILE_NOT_FOUND~; }
fault excuse = @catch(test());   // correct — @catch converts the call result to a plain fault
// void? x = test();             // this specific pattern is fine for a function SIGNATURE,
                                    // but void? cannot be the type of a stored variable
```

### `switch` on the Fault

```c3
if (catch err = ratio)
{
    switch (err)
    {
        case DIVISION_BY_ZERO: io::printn("Division by zero"); return;
        default:               io::printn("Unexpected error!"); return;
    }
}
```

### Interfacing With C

An Optional-returning C3 function crosses the C ABI as: the fault (a pointer-sized value) as the ordinary return value, and the result passed by output-reference:

```c3
// C3:  fn int? get_value();
// C:   c3fault_t get_value(int *value_ref);
```

### Contracts Are Not Part of This System

It's worth being explicit that C3 keeps two error-signaling mechanisms deliberately separate: **Optionals** are for values that can legitimately be absent or fail at runtime (a missing file, a parse failure, a network timeout). **Contracts** (`@require`/`@ensure`, §10) are for *invariant violations* — bugs — and are not intended to be routed through Optionals at all; violating a contract is unspecified behavior, checked via `assert`-style traps in safe builds, not a recoverable fault.

---

## 7. Arrays, Slices & Array Combinators

C3 offers three related-but-distinct sequence types, plus dynamic collections layered on top in the standard library (§12): **fixed arrays** (`Type[N]`, a value type, always exactly N elements, copied on assignment), **slices** (`Type[]`, a `{ptr, len}` view, bounds-checked in safe mode, never owns its data), and **vectors** (`Type[<N>]`, SIMD-backed — see §8).

### Fixed Arrays

```c3
int[4] a;                 // stack, zero-initialized, exactly 4 elements
int[3] b = { 1, 2, 3 };    // explicit size
int[*] c = { 1, 2, 3 };     // inferred size — same as int[3]
int len = c.len;             // 3
```

Unlike C, fixed arrays **do not decay to pointers**. A function that wants "a pointer to the first element" must be given one explicitly, or take the array by pointer-to-array and let the implicit `int[4]* → int*` conversion do the work:

```c3
fn int foo(int* a) { ... }
int[3] x = { 1, 2, 3 };
foo(&x);   // &x is int[3]*, implicitly converts to int* here
```

Indexing into a *pointer to* an array yields another array, not an element — a frequent gotcha coming from C:

```c3
int[3] a = { 1, 2, 3 };
int[3]* b = &a;
int x = (*b)[1];    // correct: dereference first, THEN index — x == 2
// int x = b[1];    // WRONG — this indexes the pointer itself as if b were int[3]*[N]
int y = b.[1];        // shorthand for (*b)[1]: `.` does an implicit deref before the `[]`
```

### Slices

```c3
int[3] abc = { 1, 2, 3 };
int[] slice = &abc;          // slice over the whole array — {ptr: &abc[0], len: 3}
int[] c = abc[2..2];          // { 3 } — inclusive end index
int[] d = abc[1:2];            // start:length form — { 2, 3 }
int[] e = abc[..2];             // omit start → defaults to 0
int[] f = abc[1..];              // omit end → defaults to len-1 (not allowed on raw pointers)
int[] g = abc[..];                 // whole array
int[] h = abc[^1..];                // from-the-end index: ^1 == len-1
int[] i = abc[..^1];                 // whole array minus the last element

abc[1..2] = 0;              // range-assign a scalar to a span
abc[1..2] = other[0..1];     // copy one slice's range into another's
```

Internally a slice is exactly `struct { void* ptr; sz len; }` — this layout is guaranteed and exposed as `std::core::runtime::SliceRaw` for anyone who needs to construct one manually (e.g. from FFI). Indexing a slice is bounds-checked in safe builds — this is the primary reason to prefer slices over a raw pointer-plus-length pair in a function signature: the caller gets a trap on misuse instead of silent memory corruption.

**A slice's lifetime is exactly its underlying pointer's lifetime** — nothing extends it:

```c3
fn int[] buggy_code()
{
    int[3] a;
    int[] b = a[0..1];
    return b;    // returns a slice into a stack frame that's about to be popped — BUG
}
```

### Iteration

```c3
foreach (item : arr) { io::printfn("item: %s", item); }         // by copy, type inferred
foreach (int x : arr) { ... }                                     // by copy, type explicit
foreach (idx, &item : arr) { *item = 7 + (int)idx; }               // by reference, with index
foreach_r (idx, item : arr) { ... }                                  // reverse order
```

Any type can opt into `foreach` by implementing `[]` and `len` as `@operator`-tagged methods; implementing `&[]` as well additionally enables `foreach` by reference:

```c3
macro int DynamicArray.get(DynamicArray* arr, sz i) @operator([]) { return arr.elements[i]; }
macro sz DynamicArray.count(DynamicArray* arr) @operator(len) { return arr.count; }
// Now `foreach (int i : my_dynamic_array)` works.
```

### `std::core::array` — Functional Combinators, Not a Lazy Iterator Chain

This is the one place C3's story diverges most sharply from a lazily-fused iterator pipeline: there is no adapter chain that fuses `.filter().map().take()`-style calls at compile time into a single pass. Instead, `std::core::array` provides a set of **eager, allocation-producing macros** that each walk the input once and materialize a result — closer to a small functional-array toolkit bolted onto C than to a zero-cost iterator pipeline. Every combinator below takes an explicit `Allocator`, and every one has a `t`-prefixed twin that uses the temp allocator implicitly (`@filter`/`@tfilter`, `zip`/`tzip`, `concat`/`tconcat`, and so on) — same convention as §3's allocator-taking functions generally.

```c3
import std::core::array;

int[] arr = { 1, 8, 12 };

// index_of / rindex_of / contains — linear scan, return Optional sz
sz? i = array::index_of(arr, 8);          // 1
bool has = array::contains(arr, 12);       // true

// @reduce / @sum / @product — fold with an identity value
int folded = array::@reduce(arr, 2, fn (acc, e, idx) => acc * e);  // 2*1*8*12
int total  = array::@sum(arr);                                       // 21
int prod   = array::@product(arr);                                    // 96

// @filter / @tfilter — new array of elements passing a predicate
int[] evens = array::@filter(mem, arr, fn (e, idx) => !(e % 2));   // { 8, 12 }

// @any / @all — short-circuiting predicate scans
bool any_even = array::@any(arr, fn (e, idx) => !(e % 2));   // true
bool all_pos  = array::@all(arr, fn (e, idx) => e > 0);       // true

// @indices_of — indices where a predicate holds
sz[] idxs = array::@indices_of(mem, arr, fn (e, idx) => e > 5);  // { 1, 2 }

// concat / tconcat — join two arrays/slices into a new allocation
int[] both = array::concat(mem, arr, other_arr);

// zip / tzip — pairwise combine two arrays; pads the shorter with `fill_with`
// if given, or truncates to the shorter length if not; can also apply a
// functor instead of just pairing
Pair{int, String}[] zipped = array::@zip(mem, ids, names);
int[] summed = array::@zip(mem, left, right,
                            #operation: fn int (int a, int b) => a + b,
                            fill_with: 0);

// even / odd / unlace — split an array into even-index and odd-index halves
int[] left; int[] right;
array::unlace(mem, arr, &left, &right);
```

`@sum`/`@product`/`@reduce` require the element type to actually implement the relevant operator (`+`, `*`, or whatever `#operation` needs) — enforced at compile time via `@require $defined(...)` contracts on the macro itself, so calling `@sum` on an array of a type with no `+` overload fails to compile, not fails at runtime. `@pure` marks these as side-effect-free with respect to globals for the compiler's benefit; see §10's contracts.

### Dynamic Arrays and `List`

For a growable array, use `std::collections::list::List` rather than hand-rolling one over `realloc` — see §12 for its full API surface.

```c3
alias ListStr = List{String};
fn void test()
{
    ListStr list;
    list.init(mem);
    list.push("Hello");
    list.push("World");
    foreach (s : list) { io::printn(s); }
    list.free();
}
```

`List`'s own source spells out exactly which operations shift elements and which don't. `push_front` is literally implemented as `insert_at(0, element)` — it isn't a separate fast path, it's the general shift-based insert called at index zero, which is why it costs the same O(n) as any other front-of-array insert. `remove_unordered_at`, by contrast, never shifts anything: it swaps the target element with the last one and shrinks the length, which is why it's O(1) where `remove_at` (which preserves order via a slice-copy shift) is O(n).

### Multi-Dimensional Arrays

```c3
// Declared inner-most dimension first — the REVERSE of C's outer-to-inner order.
int[4][2] array = { {1, 2, 3, 4}, {5, 6, 7, 8} };   // 2 rows of int[4]
// Access is likewise index-order-inverted relative to how it reads: array[outer][inner]
int value = array[1][3];   // second row, fourth element
// Irregular (ragged) arrays are supported directly:
int[][4] ragged = { {1}, {2,3}, {4,5,6}, {7,8,9,10} };
```

---

## 8. Vectors (SIMD)

Vectors are C3's one genuinely first-class SIMD feature — not a compiler intrinsic wrapper, not a library, a distinct built-in type category backed by hardware SIMD registers where the target supports it, with arithmetic operators overloaded element-wise as part of the language itself.

```c3
int[<2>] a = { 23, 11 };     // a VECTOR of 2 ints — note the <> vs plain []
int[<2>] b = { 2, 1 };
int[<2>] c = a * b;            // { 46, 11 } — elementwise, on real SIMD hardware where present
int[<*>] d = { 1, 2 };          // inferred length, same wildcard syntax as arrays

int[<2>] speed = { 5, 7 };
speed += 2;                    // scalar widens to { 2, 2 } automatically before the op
```

Only integer, floating-point, boolean, and pointer element types are permitted — this is a hardware-shaped constraint, not an arbitrary restriction. Note the naming collision: C3's `List` (§7, §12) is the general-purpose growable container; a `[<N>]` vector is the math/SIMD sense of the word. The two are unrelated, and it's worth being deliberate about which one a piece of code needs.

### Swizzling

```c3
int[<3>] v = { 11, 22, 33 };
int[<4>] w = v.xxzx;         // { 11, 11, 33, 11 } — x/y/z/w or r/g/b/a, either naming works
int c = w.w;                    // 11
```

Swizzle-target designated initializers also work: `int[<3>] p = { .xy = 3, .z = 100 };` is `{ 3, 3, 100 }`.

### `std::math` Vector Methods

Available via dot syntax on any numeric vector:

```c3
v.sum(); v.product(); v.max(); v.min();
v.dot(other);                     // dot product
v.length();                        // sqrt(dot(v, v)) — not on integer vectors
v.distance(other);                  // length of the difference — not on integer vectors
v.normalize();                       // unit vector — not on integer vectors
v.lerp(other, t);                     // linear interpolation
v.reflect(other);                      // reflect about `other` (assumed normalized)
v.comp_lt(other);  // ...comp_le, comp_eq, comp_gt, comp_ge, comp_ne — elementwise boolean vector
```

Scalar-only dot-methods like `ceil`/`fma` generally have vector counterparts as well.

### Cost Model

Vectors compile to native SIMD instructions on targets that support the relevant width; on targets without matching hardware support, the compiler falls back to a scalar loop with the same observable result — correctness is guaranteed regardless of whether the target can actually vectorize. `@simd` on a vector type further pins it to the exact layout of the platform's native C SIMD type, for the specific case of calling into a C API that expects that layout — most code never needs it. Runtime feature detection (whether the running CPU actually supports a given instruction set) is done via ordinary function calls into `std::os` / platform-specific modules, not a dedicated compile-time or language-level feature-detection macro.

---

## 9. Generics

### Declaring Generic Types, Functions, and Aliases

Two equivalent spellings: parameterize the whole module section, or parameterize a single declaration. Note that `<Type>` marks the parameter at **declaration**; `{Type}` supplies it at **instantiation** — the two are never interchangeable.

```c3
// Whole-module parameterization — everything below is generic over Type:
module my_module <Type>;
struct MyStruct { Type a, b; }
fn Type square(Type t) { return t * t; }

// Equivalent, single-declaration form:
module my_module;
struct MyStruct <Type> { Type a, b; }
fn Type square(Type t) <Type> { return t * t; }

// Generic aliases:
alias Pair<Type> = Type[2];
```

Generic parameters can be **types** or **compile-time constants** (int, bool, enum values):

```c3
module custom_type <Type, VALUE>;
struct Example { Type[VALUE] arr; }    // VALUE parameterizes an array SIZE, not just a type
```

### Instantiating

```c3
alias FooFloat = Foo{float, double};      // named instantiation
Foo{int, double} g;                        // anonymous, inline instantiation
```

Every generic in the same parameterized module section is instantiated **together** — pushing one struct or function through monomorphization pulls its siblings along, but two generics with *different* parameter names in the same module are tracked as genuinely separate generics, and using one doesn't instantiate the other:

```c3
module abc <Test>;
fn Test test1(Test a) { return a + 1; }        // "generic 1"
struct Foo { Test a; }                           // also "generic 1" — same param name

module abc <Test2>;
fn Test2 test3(Test2 a) { return a * a; }         // "generic 2" — different param name

fn void main() { Foo{int} a; }   // instantiates Foo and test1, but NOT test3
```

### Contracts as Bounds

There's no first-class bounds syntax on a generic parameter list — instead, put a contract on the generic declaration itself, checked at instantiation time:

```c3
<*
 @require $assignable(1, TypeB) && $assignable(1, TypeC)
*>
module vector <TypeA, TypeB, TypeC>;
```

Instantiating with parameters that fail the contract is a compile error at the instantiation site, with the violated `@require` printed as the diagnostic. `$defined(expr)` (§10) is the workhorse predicate here: `@require $defined((Key){}.hash())` on `HashMap`'s module declaration is exactly how the standard library enforces "the key type must have a `.hash()` method," for instance.

Contracts placed on types and identifiers combine, but contracts on generic *functions and macros* do not carry over to the module's aggregated contract — a function-level `@require` is only checked when that specific function is actually invoked, not merely when the type is instantiated:

```c3
module foo;

<* @require Test::kind == TypeKind.SIGNED_INT *>
struct Foo <Test> { Test a; }

<* @require Test::size < 4 *>
fn Test testme(Test t) <Test> { return t * 2; }

fn void main()
{
    // This is fine — Foo's contract doesn't apply to testme, and testme's
    // own contract is only checked if testme is actually called:
    Foo{long} x;
}
```

### Methods on Generic Types

```c3
module foo;
struct Foo <Type> { Type a; }

module bar;
import foo;
fn Type Foo.add(self, Type b) => self.a + b;   // extends EVERY instantiation of Foo

fn void main()
{
    Foo{int} f1 = { 3 };
    Foo{double} f2 = { 3.4 };
    io::printn(f1.add(5));   // works for both — the method itself stays generic
}
```

You can alternatively extend one **specific** instantiation only — in that case the method cannot reference the generic parameter, since from its point of view there isn't one:

```c3
fn int Foo{int}.add(self, int b) => self.a + b;   // only Foo{int} gets this method
// Foo{double} has no .add at all, unless the generic version above also exists
```

---

## 10. Macros & Compile-Time Execution

C3's macro system replaces the C preprocessor entirely — no textual substitution, no token-pasting-as-primary-mechanism, no invisible magic. It is deliberately more constrained than a scripting-language-style macro system: **top-level compile-time evaluation is limited** to `@feat` (feature-flag gating) and, inside generics, `@if` — full `$if`/`$for`/`$foreach`/`$switch` compile-time execution is only available *inside* function and macro bodies, not at the top level of a file. The stated reason: unrestricted top-level compile-time code generation is exactly what makes large C/C++ codebases develop invisible, hard-to-trace "magic" over time, and C3 trades away some expressive power specifically to keep every top-level declaration visible to a simple, non-macro-expanding IDE. Local function scopes have the full range of compile-time evaluation available, since that's where the trade favors expressiveness over top-level visibility.

### The Sigils: `$`, `#`, `@`

- **`$name`** — a compile-time value or type, evaluated and folded during compilation. `$Type`, `$n`, `$x` are all compile-time parameters/variables.
- **`#name`** — a macro parameter with **deferred evaluation**: the expression is bound at the call site but not evaluated until it's used inside the macro body, and re-evaluates each time it's referenced. This is what makes true expression-macros (macros that can be assigned into, or that need the caller's exact lvalue) possible.
- **`@name`** — required on the macro's *declared name* whenever the macro uses `#`-parameters or a trailing body (`@body(...)`). The `@` is a reader-facing warning: "this call may do more than an ordinary function call would" — macros that don't use these features behave like ordinary functions and don't need it.

```c3
macro foo(a, b) { return a(b); }          // no # / @body → plain name is fine
fn int square(int x) { return x * x; }
fn int test() { return foo(&square, 2) + 1; }   // 9 — ordinary, eagerly-evaluated call
```

```c3
macro @foo(#a, b, #c) { #c = #a(b) * b; }   // uses #, so the name MUST start with @

macro long @fib(long $n)                     // $-only params: fully compile-time evaluable
{
    $if $n <= 1:
        return $n;
    $else
        return @fib($n - 1) + @fib($n - 2);
    $endif
}
const long FIB19 = @fib(19);   // folds to 4181 at compile time — no runtime recursion at all
```

Note the deliberate asymmetry: inside `@fib`, the comparison has to be against `$n` (the compile-time parameter), not a plain `n` — even if the actual call-site argument happens to be a compile-time constant, using the non-`$` name in the condition is a compile error. This is intentional: it keeps "what gets compiled away" a property of how the macro is *written*, not an accident of how it happens to be *called*.

### Deferred Evaluation in Practice: Why the `#` Matters

```c3
<* @require $defined(#a = #b, #b = #a) *>
macro void @swap(#a, #b)
{
    var temp = #a;
    #a = #b;
    #b = temp;
}
fn void test() { int a = 10; int b = 20; @swap(a, b); }
// Expands correctly to operate on the CALLER's actual a and b.
```

Contrast with a naive version that takes `a`/`b` as ordinary (eagerly-evaluated) parameters — it would copy the values in, swap the copies, and silently do nothing to the caller's variables:

```c3
macro void badswap(a, b) { var temp = a; a = b; b = temp; }

fn void test()
{
    int a = 10; int b = 20;
    badswap(a, b);
    // a and b are UNCHANGED — badswap swapped local copies __a/__b, never touched the caller's
}
```

The `#` is the difference between a macro that manipulates the caller's lvalues and one that just receives their values.

### Trailing Blocks — Macro-Level "Lambdas" With No Actual Closure

```c3
macro @foreach(a; @body(index, value))
{
    for (int i = 0; i < a.len; i++) { @body(i, a[i]); }
}
fn void test()
{
    double[] a = { 1.0, 2.0, 3.0 };
    @foreach(a; int index, double value)
    {
        io::printfn("a[%d] = %f", index, value);
    };   // <- trailing `;` required: this whole call, body and all, is an EXPRESSION
}
```

The trailing `;` is not a typo or style choice — every macro call, trailing body or not, is grammatically an expression, and terminating an expression with `}` alone would make the grammar ambiguous. Consider `int a = @test() {} + @test() {}` followed by `*b = 123;` on the next line — without a required `;`, there's no way for the parser to know where the expression ends and the next statement begins. This is a real, deliberate tradeoff C3 documents explicitly: a small, consistent syntactic cost in exchange for a substantially simpler grammar.

### Vaargs Inside Macros

```c3
macro compile_time_sum(...)
{
    var $x = 0;
    $for var $i = 0; $i < $vaarg.len; $i++:
        $x += $vaarg[$i];
    $endfor
    return $x;
}
```

`$vaarg.len`, `$vaarg[idx]`, `$stringify($vaarg[idx])`, `$Typefrom($vaarg[idx])`, and splatting (`...$vaarg`, or a sub-range `...$vaarg[2..4]`) round out the vaarg toolkit — this is also how overload-by-arity dispatch is done in idiomatic C3, since there's no first-class function overloading:

```c3
fn void Obj.func1(&self, String... args) @private { }   // vaargs variant
fn void Obj.func2(&self, Foo* pf) @private { }            // single-pointer variant
macro void Obj.func(&self, ...)
{
    $if $vaarg.len == 1 &&& $Typeof($vaarg[0]) == Foo*:
        return self.func2($vaarg[0]);
    $else
        return self.func1(...$vaarg);
    $endif
}
// Now both obj.func("a", "b") and obj.func(&my_foo) resolve correctly.
```

(`&&&` above is compile-time `&&` with short-circuit type-checking on the right-hand side — it lets `$Typeof($vaarg[0])` go unevaluated, and thus not error, when `$vaarg.len` is already known to be `0`.) This exact pattern — a `macro` with C-style `...` vaargs inspecting `$vaarg.len` and `$Typeof` to dispatch to one of several differently-shaped functions — is genuinely how the standard library itself solves the "overloading" problem; it is documented idiom, not a workaround to be embarrassed about.

### Compile-Time Introspection

```c3
sz alignment = Foo::alignment;
sz field_count = Foo::members.len;
String name = Foo::name;

macro print_fields($Type)
{
    $foreach $field : $Type::members:
        io::printfn("Field %s, offset: %s, size: %s, type: %s",
                     $field.name, $field.offset, $field.size, $field.type.name);
    $endforeach
}
```

### Compile-Time Function Reference

| Function | Purpose |
|---|---|
| `$assert(expr)` | Compile-time assertion |
| `$defined(expr)` | `true` if `expr`/declaration is valid; the workhorse of contract-based generic bounds |
| `$echo(msg)` | Print during compilation |
| `$embed(path)` | Embed a file's raw bytes as a `char[]` constant at compile time |
| `$error(msg)` | Force a compile error |
| `$eval(str)` | Turn a compile-time string into the variable/function it names |
| `$exec(cmd, args, stdin)` | Run an external program (or compile-and-run a C3 script) and splice its stdout in as source text — requires `--trust=full` |
| `$expand(str)` | Turn a compile-time string into code |
| `$feat(NAME)` | Check a `-D NAME` feature flag |
| `$include(path)` | Textually include another file's top-level content — requires `--trust=include` or higher |
| `$stringify(#expr)` | Turn an expression into its literal source text, as a string |
| `$Typeof(expr)` | The type of an expression, without ever evaluating it (no side effects) |
| `$Typefrom(typeid_or_str)` | A type, from a compile-time `typeid` or a string naming one |

`$stringify` is what powers ergonomic debug-printing macros:

```c3
macro @show(#expr) { io::printfn("%s == %s", $stringify(#expr), #expr); }
int num = 5;
@show(num);   // prints "num == 5"
```

### Conditional Compilation: `@feat`, Not `#ifdef`

At the top level, feature-gating a declaration uses `@feat`, combining flags with `& | !` and parentheses (a top-level comma means `|`; repeating the attribute means `&`):

```c3
fn void foo_win32() @feat(WIN32) { ... }
fn void posix_not_mac() @feat(POSIX | !MACOS) { ... }
module network::linux @feat(LINUX);   // applies to every declaration in the section
```

Inside generics specifically, `@if` conditionally includes a field or declaration *per instantiation*, based on the generic parameters:

```c3
struct Container <Ty>
{
    Ty first;
    Ty last @if(Ty::kind == TypeKind.SIGNED_INT);   // only present when Ty is a signed int
}
```

### Contracts — Design by Contract, Compiled Into Asserts

Contracts are pre-/post-condition annotations on a function or macro, written in a special `<* ... *>` comment block immediately preceding the declaration. They are **not** part of the Optional error-handling system (§6) — a contract violation signals a bug, not a recoverable runtime condition.

```c3
<*
 @param foo : "the number of foos"
 @require foo > 0, foo < 1000
 @return "number of foos x 10"
 @ensure return < 10000, return > 0
*>
fn int test_foo(int foo) { return foo * 10; }
```

In debug/safe builds this compiles to something close to:

```c3
fn int test_foo(int foo)
{
    assert(foo > 0);
    assert(foo < 1000);
    int _return = foo * 10;
    assert(_return < 10000);
    assert(_return > 0);
    return _return;
}
```

**Contracts are legal optimization fodder, not just runtime checks** — the compiler is allowed to assume a satisfied `@ensure` is always true, even in fast builds where the assert itself has been stripped:

```c3
fn int test_example(int bar)
{
    if (test_foo(bar) == 0) return -1;   // @ensure said return > 0, so this branch is
    return 1;                              // provably dead — may be optimized away entirely
}
```

Parameter-direction annotations (`[in]`, `[out]`, `[inout]`) document and partially enforce read/write access for pointer parameters; prefixing with `&` (`[&in]`) additionally asserts non-null:

| Annotation | Readable? | Writable? |
|---|---|---|
| (none) | Yes | Yes |
| `[in]` | Yes | No |
| `[out]` | No | Yes |
| `[inout]` | Yes | Yes |

```c3
<* @param [&in] i *>
fn void read(int* value) { io::printf("%d", *value); /* (*value)++; ← compile error */ }
```

These checks are **locally syntactic, not whole-program** — a function can still "lie" about its own contract by routing a write through a second, unconstrained pointer alias; the compiler is not obligated to catch that. Contract-checking depth is itself tiered, from "parse only" to "full static analysis"; the reference compiler `c3c` implements up to caller-side `@require` re-checking at the time of writing.

`@pure` on a function or a specific call site tells the compiler "this doesn't touch globals" for optimization purposes — like `@require`/`@ensure`, this is a promise the compiler is allowed to *trust*, not one it's obligated to *verify*; violating it produces working-looking code that misbehaves under optimization, not a compile error.

Contracts on **macros** commonly lean on `$defined` to give a much better error message than "type mismatch somewhere":

```c3
<*
 @param x : "value to square"
 @require types::is_numerical($Typeof(x)) : "cannot multiply"
*>
macro square(x) { return x * x; }
// square("hello");  → "Error: cannot multiply \"hello\"" — not a generic type error
```

---

## 11. Concurrency

`std::thread` provides a cross-platform layer over native OS threading primitives — no async runtime, no green threads. Thread safety is a matter of discipline and the primitives below, checked (where checked at all) at runtime, not statically by the type system.

### Thread Management

```c3
fn int worker(void* arg) { /* ... */ return 0; }

Thread t;
t.create(&worker, arg, settings)!;     // settings defaults to {} if omitted
int exit_code = t.join()!!;             // block until done, retrieve exit code
t.detach()!;                              // OR: let it run independently; OS reclaims resources on exit
t.set_priority(REALTIME);                  // also DEFAULT, BACKGROUND, LOW, NORMAL, HIGH

thread::current();     // the calling thread's own handle
thread::yield();         // relinquish the CPU
thread::sleep(duration);  // suspend for a Duration
thread::sleep_ms(50);      // suspend for a given number of milliseconds
thread::exit(0);           // terminate current thread; also tears down its temp allocator arena
```

`Thread.create` can fail with `INIT_FAILED` or `INVALID_THREAD_SETTINGS`; `Thread.join` can fail with `THREAD_NOT_FOUND` if the thread cannot be found. `ThreadPriority` is a six-value enum: `DEFAULT, BACKGROUND, LOW, NORMAL, HIGH, REALTIME`.

### Mutexes

Four variants: `Mutex` (standard, non-recursive), `RecursiveMutex` (same thread can lock repeatedly), `TimedMutex` (adds a timeout), `TimedRecursiveMutex` (both). All four are thin typedefs over a shared native mutex implementation — `RecursiveMutex` and `TimedRecursiveMutex` are declared `inline` over `Mutex`/`TimedMutex` respectively, so a recursive mutex "is-a" mutex for the purposes of §4's `inline` subtyping.

```c3
Mutex m;
m.init()!;
defer m.destroy();
m.lock()!;
defer m.unlock();
// ... critical section ...

// Or, scoped via the built-in macro (defer-based under the hood — see §3's Guard pattern):
m.@in_lock()
{
    // critical section; unlocked automatically at block exit, even on early return
};
```

`TimedMutex` additionally exposes `lock_timeout(ms)`, returning `LOCK_TIMEOUT` on expiry rather than blocking forever.

### Condition Variables and One-Time Init

```c3
ConditionVariable cv;
cv.init()!;
defer cv.destroy();
cv.wait(&m);                                  // block on the mutex until signaled
cv.wait_timeout(&m, duration_or_ms)!;           // bounded wait — accepts a Duration or a raw ms count
cv.wait_until(&m, deadline);                     // absolute-time wait
cv.signal();  cv.broadcast();

OnceFlag once;
once.call(&init_function);   // init_function runs exactly once, across ALL threads
```

Both timed-wait variants return `WAIT_TIMEOUT` if the deadline passes before a signal arrives.

### Channels — Four Shapes, Chosen by Buffering Need

All four channel types live under `std::thread::channel <Type>`, are heap-allocated pointer types returned from a `create_*` function, and share the same close/fault vocabulary: `push`/`try_push`, `pop`/`try_pop`, and `close`. The blocking calls (`push`, `pop`) wait on a condition variable; the `try_` variants return immediately with a fault instead of blocking.

| Channel | Semantics | Use when |
|---|---|---|
| `BufferedChannel{T}` | Fixed-capacity ring buffer; blocks only when full/empty | Producer/consumer with some slack tolerable |
| `UnbufferedChannel{T}` | Holds exactly one in-flight value — a push must wait for a pop before the next push can proceed | You need send/receive to rendezvous closely |
| `UnboundedChannel{T}` | Backed by a growable deque; push never blocks on capacity | Producers must never stall, and unbounded memory growth is acceptable |
| `OneShotChannel{T}` | Exactly one value, one send, one receive, ever | Request/response, a one-time signal between two threads |

```c3
BufferedChannel{int}* ch = channel::create_buffered(mem, size: 16)!;
defer ch.destroy();
ch.push(42)!;
int v = ch.pop()!;
```

```c3
// From the stdlib's own doc comment for OneShotChannel:
OneShotChannel{int}* channel = channel::create_one_shot(mem)!;
defer channel.destroy();

Thread thread;
thread.create(fn int(void* arg)
{
    OneShotChannel{int}* channel = arg;
    channel.push(123)!!;
    return 0;
}, (void*)channel)!!;
defer thread.join();

int value = channel.pop()!!;
```

Fault vocabulary across all four: `CHANNEL_CLOSED` (operating on a closed, empty channel — or, for `OneShotChannel`, a channel that was closed before sending or whose one value was already consumed), `CHANNEL_BLOCKED` (a `try_push` found the channel full), `CHANNEL_EMPTY` (a `try_pop` found the channel empty).

### Thread Pools — Two Distinct Types, Not Interchangeable

C3's stdlib ships two genuinely different thread pool implementations, and picking the wrong one for the job is a real footgun:

**`ThreadPool`** (`std::thread`) is the current, actively maintained pool: dynamically sized, spawns workers lazily up to `max_threads`, backed by a growable deque for its work queue, and supports an optional bounded queue capacity, worker keep-alive/idle-timeout, and graceful vs. immediate shutdown.

```c3
ThreadPool pool;
pool.init(mem, max_threads: 8, queue_capacity: 0)!;   // 0 = unbounded queue
defer pool.destroy();                                   // graceful: finish queued work, then join

pool.add_task(&my_task_fn, arg)!;         // blocks if a bounded queue is full
pool.try_add_task(&my_task_fn, arg)!;     // never blocks — THREAD_QUEUE_FULL if the queue is full

sz pending = pool.queue_count();
int busy = pool.busy_count();
int alive = pool.worker_count();
```

`ThreadPool.destroy()` lets queued work finish before joining every worker; `ThreadPool.destroy_now()` discards queued work but still lets in-flight jobs finish. Both are safe to call on an already-shut-down or never-initialized pool.

**`FixedThreadPool`** (`std::thread::threadpool`) predates `ThreadPool` and is explicitly marked `@deprecated` in its own source, with a comment reading "Please do not use this one in production." It spawns exactly `threads` worker threads up front, uses a fixed-size backing array rather than a growable queue, and accepts heterogeneous `any[]`-typed task arguments (`ThreadPoolFn = fn void(any[] args)`) rather than a single `void*`. New code should reach for `ThreadPool`; `FixedThreadPool` exists for compatibility with code written against it before `ThreadPool` was added.

```c3
// FixedThreadPool — legacy, deprecated, shown for recognition only:
FixedThreadPool pool;
pool.init(threads: 4)!;
pool.push(&my_variadic_task, arg1, arg2)!;   // THREAD_QUEUE_FULL if the queue is full
pool.join();          // wait for all queued work to drain
pool.stop_and_destroy();
```

### What C3 Deliberately Does Not Provide Here

There is no shared-ownership smart pointer distinguishing atomic from non-atomic reference counting, because there's no ownership-tracking type system to hang that distinction on in the first place — shared mutable state across threads is just a pointer plus a `Mutex` (or an atomic type, for lock-free counters), same as it would be in C. There is likewise no compile-time marker preventing a non-thread-safe type from crossing a thread boundary; passing the wrong thing to a thread function is a runtime bug, not a type error, and the burden of avoiding it sits entirely with the programmer, same as in C. Semaphore support does not exist in the standard library as of this writing, though it has been proposed upstream specifically to make thread-pool-style code more efficient than polling a mutex.

---

## 12. Standard Library

### Module Map

The essentials, per the language's own FAQ, are:

- **`std::core`** (auto-imported into every file): `core::array` (see §7's combinators), `core::builtin` (`unreachable()`, `bitcast()`, `@catch`, `@ok` — used without a module prefix), `core::cinterop` (types matching platform C types), `core::dstring` (the dynamic string builder), `core::mem` (`malloc`-family, atomic/volatile load-store), `core::string` (conversions, splitting, searching)
- **`std::collections`**: `List{Type}` and `HashMap{Key,Value}` are, per the docs, the two most frequently reached-for; also `HashSet`, `LinkedList`, `Deque`, `RingBuffer`, `OrderedMap`/`OrderedSet` (insertion-order-preserving, using `ORDEREDONHEAP` rather than `ONHEAP` for their static-heap-init constant — a real naming inconsistency worth knowing about, not a typo in this document), `SortedMap` (skip-list backed, `@mustinit` — see §3), `Object` (a JSON-shaped dynamic variant container)
- **`std::io`**: `io::file` (files), `io::path` (cross-platform paths), stream types under `io::stream`
- **`std::net`** (sockets), **`std::thread`** (§11), **`std::time`** (dates, durations, timers), **`std::math`** (including vector methods, §8), **`libc`** (direct libc calls where needed), **`std::os`** (OS-specific code)

### `List{Type}` — the Dynamic Array

| Operation | Complexity | Why |
|---|---|---|
| `push(element)` | Amortized O(1) | Appends past the current length, growing the backing array when needed |
| `pop()` | O(1) | Shrinks the length and returns the last element; no shifting |
| `push_front(element)` | O(n) | Implemented as `insert_at(0, element)` — a full shift, not a special case |
| `pop_first()` | O(n) | Implemented as `remove_at(0)` — same shift |
| `get(index)` / `set_at(index, v)` | O(1) | Direct index into the backing array |
| `insert_at(index, element)` | O(n) | Shifts every element after `index` up by one |
| `remove_at(index)` | O(n) | Shifts every element after `index` down by one, preserving order |
| `remove_unordered_at(index)` | O(1) | Swaps the target with the last element instead of shifting — does NOT preserve order |

```c3
List{int} list;
list.init(mem);            // or list.tinit() for the temp allocator; or leave uninitialized
                              // and let ZII lazily init it on tmem at first push
list.push(1); list.push(2);
int x = list[0];              // @operator([]) is implemented — indexing "just works"
list.free();                    // required when heap-backed; temp-backed lists are freed by @pool
```

### `HashMap{Key,Value}` — Associative Array

Requires the key type to implement `.hash()`, enforced by a module-level contract (`@require $defined((Key){}.hash())`). Average O(1) for `set`/`get`/`remove`/`has_key`.

```c3
HashMap{String, int} counts;
counts[key] = (counts[key] ?? 0) + 1;    // [] and []= are @operator overloads
counts.set("a", 1);                        // equivalent, explicit spelling
int? v = counts.get("a");                    // Optional — NOT_FOUND fault if absent
bool has = counts.has_key("a");
Key[] ks = counts.keys(mem);                                          // or .tkeys() for temp
counts.remove("a");
counts.free();
```

`HashMap` declares that it implements the `Printable` interface (`struct HashMap (Printable)`) and provides a `to_format` method, so `io::printfn("%s", counts)` prints a readable `{ key: value, ... }` dump directly without any extra work on your part. `SortedMap` implements `Printable` the same way.

`Printable` itself is a small, two-method optional interface — both methods are `@optional`, so a type can implement either, both, or neither:

```c3
interface Printable
{
    fn String to_constant_string() @optional;
    fn sz? to_format(Formatter* formatter) @optional;
}
```

`to_format` (writing directly to a `Formatter*`) is the non-allocating path and is what most stdlib types implement; `to_constant_string` is for types that can return a fixed, unowned string without formatting machinery at all. If neither is implemented, the formatter falls back to reflectively dumping struct members.

### `LinkedList{Type}` — Doubly-Linked List

O(1) push/pop at either end, O(1) insert/remove given a known position, O(n) random access and O(n) linear `index_of`. Choose this over `List` specifically when insert/remove in the *middle* dominates and index-based random access does not.

### `RingBuffer{Type}` — Fixed-Capacity FIFO

O(1) push (to tail) and pop (from head), no element-shifting, no reallocation — the right structure for a bounded producer/consumer buffer where you want hard, fixed memory use. `Deque{Type}` gives you the double-ended version, built on top of `List` internally rather than a fixed ring.

### Strings

Four related types, each with a distinct contract (see also §2's naming discussion and §4):

| Type | Definition | Use for |
|---|---|---|
| `String` | `typedef inline char[]` | The default. UTF-8, sliceable, comparable, no null-terminator required |
| `ZString` | `typedef inline char*` | C-interop: null-terminated, like `char*` in C |
| `WString` | `typedef inline Char16*` | C-interop on UTF-16 platforms (Win32) |
| `DString` | opaque pointer, implements `OutStream` | A dynamic string **builder** |

```c3
String s = "hello";
s.starts_with("he");  s.ends_with("lo");
sz? i = s.index_of("ll");         // Optional sz
String t = s.trim();                // also trim_left / trim_right
String u = s.replace(mem, "l", "L");  // allocating — also treplace() for the temp allocator
String joined = string::join(mem, parts, ", ");

int? n = string::to_integer{int}(s, base: 10);    // MALFORMED_INTEGER / INTEGER_OVERFLOW faults

DString b;                          // ZII: lazily inits on first use — but NOTE, unlike List
                                     // or HashMap, DString has no ONHEAP constant, so a global
                                     // DString can only be pointed at the heap by explicitly
                                     // calling .init(mem) at runtime — see §3
b.appendf("Hello %s", "World");
b.insert_at(5, ",");
b.append("!");
b.append_char('?');
io::printn(b);                       // "Hello, World!?"
String view = b.str_view();            // borrowed view — invalidated by further mutation
String owned = b.copy_str(mem);          // independent, allocated copy
```

Formatting functions, chosen by where the result should live:

| Function | Destination | Returns |
|---|---|---|
| `string::format(allocator, fmt, ...)` | Caller-supplied allocator | `String` |
| `string::tformat(fmt, ...)` | Temp allocator | `String` |
| `string::bformat(buf, fmt, ...)` | Fixed caller-supplied buffer, no allocation | `String` |
| `string::tformat_zstr(fmt, ...)` | Temp allocator | `ZString` |

`io::printfn` accepts `%s` for essentially any type, not just strings — it routes through the same `Printable` interface described above.

### I/O: Streams and Files

Two core interfaces underlie everything — `InStream` and `OutStream`. Anything implementing them (a `File`, a `ByteBuffer`, a `DString`, a network socket) is interchangeable wherever a stream is expected:

```c3
// InStream
bytes_read = stream.read(buffer);
byte = stream.read_byte();
stream.seek(offset, whence);
n = stream.available();
stream.close();

// OutStream
stream.write(bytes);
stream.write_byte(c);
stream.flush();
stream.close();
```

```c3
File f = file::open("data.txt", "r")!;
defer (void)f.close();
char[1024] buf;
usz n = f.read(buf)!;
```

`path::mkdir()` / `path::rmdir()` / `path::ls()` / `path::cwd()` round out cross-platform directory handling.

### JSON

`std::encoding::json` parses into `Object`, the same dynamic variant container used generally for "I don't know the shape ahead of time" data — it can hold ints, floats, strings, nested `List`-shaped or `HashMap`-shaped structure, and frees recursively with one `.free()` call. Both strict JSON and JSONC (JSON-with-comments) are supported as explicit parse modes.

---

## 13. Testing

### `@test`

```c3
module mymodule @test;   // every function in this module SECTION defaults to @test
// or, mark functions individually:
fn void test_addition() @test
{
    assert(1 + 1 == 2);
}
```

`@test`-marked functions are compiled into the binary only when tests are being run (`c3c compile-test` or equivalent), and excluded otherwise — the attribute is on the function or module section itself, rather than a separate conditional-compilation block wrapping it.

### `assert`

```c3
assert(condition);
assert(condition, "message: %s", detail);
```

`assert` runs in both debug and release builds by default — there's a separate compiler switch to strip asserts for a release build, rather than a language-level split between an always-on and a debug-only assert. `unreachable()` marks a branch the author guarantees can't be reached; reaching it anyway traps in safe builds and is undefined behavior in fast ones — see §1's UB table.

### Contracts Double as Test Coverage

Because `@require`/`@ensure` compile into runtime asserts in safe/debug builds (§10), a well-contracted function is partially self-testing before a single `@test` function is written — violating a precondition anywhere in the test suite surfaces as a trap with a clear message, not a downstream assertion failure three calls later.

### `@benchmark`

```c3
fn void bench_parse() @benchmark
{
    // timed when benchmarks are explicitly run; excluded from ordinary compilation otherwise
}
```

### Fixtures via `defer`

There's no dedicated fixture/teardown attribute — the same `defer`-based cleanup pattern from §3 covers it directly, since a `@test` function is an ordinary function as far as scope-exit semantics go:

```c3
fn void test_with_fixture() @test
{
    TestDb db = testdb::create(tmem);
    defer db.destroy();     // runs even if an assert() above it fails and unwinds/traps
    // ... test body ...
}
```

---

## 14. API Design Patterns

### Named Constructors Over an Overloaded `new`

There's no function-overloading, so the "several ways to construct a value" problem is solved the same way it is in most C-adjacent languages without overloading: distinct, descriptively-named functions.

```c3
fn DateTime now() { ... }
fn DateTime from_timestamp(long ts) { ... }
fn DateTime from_ymd(int y, int m, int d) { ... }
```

### Builder Pattern

```c3
struct ServerBuilder { String host; ushort port; uint max_connections; }

fn ServerBuilder new_builder() => { .host = "localhost", .port = 8080, .max_connections = 100 };
fn ServerBuilder ServerBuilder.host(self, String host) { self.host = host; return self; }
fn ServerBuilder ServerBuilder.port(self, ushort port) { self.port = port; return self; }
fn Server? ServerBuilder.build(self)
{
    if (self.port == 0) return INVALID_PORT~;
    return { self.host, self.port, self.max_connections };
}
// server_builder::new_builder().host("api.example.com").port(443).build()!
```

Parameter names should shadow the field they set (`host`, not `h`) — same convention as §2's general naming guidance. This isn't spelled out verbatim anywhere in the official naming-conventions writeup, but it follows directly from it: the stdlib's snake_case, self-documenting style (§2) exists precisely so a parameter name carries its own meaning without a comment, and a single-letter parameter throws that away for no benefit — especially in a builder, where the setter's whole job is to be self-explanatory at the call site.

### The `Params`/`Settings` Split — One-Shot vs. Long-Lived Parameter Structs

A frequent shape: instead of an 8-argument constructor, take one plain-data struct. The convention distinguishes two flavors by *lifetime*, not by shape — both are just structs with public fields and sane defaults.

| Question | `Params` | `Settings` |
|---|---|---|
| Passed once, per-instance, to a constructor? | Yes | |
| Owned by a long-lived object, read back later? | | Yes |
| Built inline at a single call site with `{ .field = value }`-style literals? | Yes | |

```c3
struct WindowParams { uint width; uint height; String title; }
fn Window create_window(WindowParams params) { ... }
create_window({ .width = 1920, .height = 1080 });   // rest zero/default via ZII

struct PoolSettings { int max_threads; sz queue_capacity; }
struct WorkerPool { PoolSettings settings; }
fn WorkerPool WorkerPool.new(PoolSettings settings) => { .settings = settings };
fn PoolSettings* WorkerPool.settings(&self) => &self.settings;   // still readable post-construction
```

The `WindowParams` value only ever exists at the call site — `create_window` reads it and it's gone. `PoolSettings` is different: `WorkerPool` keeps a copy for the rest of its life, and something later might reasonably call `pool.settings().max_threads` to check what it was configured with. That's the entire distinction — not the shape of the struct, which is identical in both cases, but whether anything still holds a reference to the values after construction returns. §11's `Thread.create(&worker, arg, settings)` is the same `Settings`-suffix idea already at work: a plain-data struct with defaults, handed to a constructor, whose fields a caller might still care about later (e.g. `t.set_priority(...)` reading back against whatever `settings` established).

### `typedef` vs. `alias` — Real New Type vs. Pure Rename

This distinction is the one most worth internalizing early, because it looks like a style choice and is actually a semantics choice:

```c3
alias CharPtr = char*;      // ALIAS — CharPtr and char* are the exact same type, always
typedef Meters = double;    // TYPEDEF — Meters is a NEW, distinct type
Meters m = 1.0;               // literal conversion works — 1.0 converts to double first
double d = 5.0;
// m = m + d;               // ERROR — Meters and double don't implicitly mix
m = m + (Meters)d;             // explicit cast required
```

Use `alias` purely to shorten a spelling with zero semantic weight (function pointer types, in particular, *must* be aliased — there's no anonymous function-pointer-type syntax at a use site). Use `typedef` for a genuine newtype — a distinct type sharing its underlying representation with the base type, rather than wrapping it in a one-field struct — and methods attach to the `typedef` directly:

```c3
typedef UserId = ulong;
typedef ProductId = ulong;
fn User? get_user(UserId id) { ... }
// get_user((UserId)some_product_id);   // still compiles if explicitly cast — typedef doesn't
                                            // prevent MISUSE, it only prevents ACCIDENT
```

`typedef ... inline` sits between the two: implicit conversion **to** the base type, but not **from** it — useful when an API needs to hand your newtype to something expecting the raw type, without opening the door to accidentally constructing your newtype from a bare value elsewhere:

```c3
typedef ZString = inline char*;
ZString z = "hi";
char* raw = z;         // implicit — fine, ZString "is-a" char* for this direction
// ZString z2 = raw;   // NOT implicit — must cast, same asymmetry as struct `inline` subtyping
```

### Suffix Conventions

| Suffix | Contract |
|---|---|
| `XxxParams` | Plain-data, one-shot construction parameters; all fields public, sensible zero/defaults |
| `XxxSettings` | Same shape as `Params`, but owned by a long-lived object and read back over its lifetime |
| `XxxBuilder` | Multi-step construction; chained calls; ends in `.build()` returning an `Optional` or plain value |
| `Guard` | RAII-by-convention: acquired, paired with a `defer`-released cleanup; never given copy-friendly value semantics |
| `Xxx` + `.hash()` method | Required contract for anything used as a `HashMap` key |

### Naming Conventions Beyond Casing

Two conventions worth knowing on top of §2's casing rules, drawn directly from the standard library's own practice: a function or method with `new` in its name will in general perform one or more allocations and can typically take an optional allocator; a function or method with `temp` in its name will usually allocate using the temp allocator instead. `free` releases all memory associated with a value; `destroy` is similar to `free` but also indicates that other resources (file handles, OS handles, and the like) are released alongside the memory. In some corners of the library, `close` is used in place of `destroy` for the same idea.

### There Is No Single "App Error" Type — `fault` Is the Only Error-Value Type

Because C3's error channel is the Optional's fault tag rather than an arbitrary user-defined error *type* (§6), there's no equivalent design tension between "structured library errors" and "flexible application errors with context chains." Every fallible function returns `SomeType?`, and every failure is some `fault` value, declared with `faultdef`:

```c3
faultdef PARSE_UNEXPECTED_EOF, PARSE_INVALID_BYTE, PARSE_OVERFLOW;

fn Ast? parse(char[] data)
{
    if (data.len == 0) return PARSE_UNEXPECTED_EOF~;
    // ...
}
```

There's no per-module error-enum to define and no message-chain builder to wire up — the tradeoff C3 makes here (per its own FAQ reasoning in §6) is a smaller, uniform error surface at the cost of not being able to attach arbitrary structured payload data to a specific failure the way a richly-typed error variant with named fields can. If a failure genuinely needs to carry data beyond "which fault," the common pattern is a `TypeName?`-returning function paired with a separate way to fetch details (a thread-local/last-error slot, or an out-parameter) — there is no single blessed idiom for this in the standard library.

A function can also inherit the faults of another function or macro it calls, documented with `@return?`:

```c3
<*
 @return? check_triangle!, io::EOF
*>
fn TriangleKind? get_triangle_kind(Triangle* triangle)
{
    check_triangle(triangle)!;
    // ...
}
```

`check_triangle!` (with a trailing `!`) means "include every fault `check_triangle` itself might return"; `io::EOF` adds one more of `get_triangle_kind`'s own on top.

### Overload-by-Arity via Macro Dispatch

Since C3 has no function overloading, the standard idiom for "one call site, several implementations depending on what was passed" is a `macro` with C-style vaargs (`...`) that inspects `$vaarg` and dispatches — see §10 for the full mechanism and the real example straight from the stdlib.

---

## 15. Attributes Reference

An attribute is a compile-time annotation — `@name` or `@name(args)` — attached to a function, type, variable, global, constant, or member. C3 ships around sixty built-in attributes; this section is the full inventory. A number of them already have real, worked-through treatment earlier in this document, because they're load-bearing enough to explain in context rather than as a table row — those are cross-referenced rather than re-explained. Everything else gets its full entry here.

### Already Covered In Depth Elsewhere

| Attribute | What it does | Where |
|---|---|---|
| `@align(n)` | Sets a minimum alignment; can only increase it, never decrease | §4 |
| `@packed` | Forces every member's alignment to 1 | §4 |
| `@compact` | Like `@packed`, but recursive — no padding anywhere in the tree | §4 |
| `@nopadding` | Compile error if padding would be needed, rather than silently removing it | §4 |
| `@mustinit` | Forbids `@noinit` on variables of this type; ZII does not apply | §1, §3 |
| `@noinit` | Opts a variable out of zero-initialization; must be assigned before use | §1 |
| `@dynamic` | Marks a method reachable through interface dispatch | §5 |
| `@optional` | Marks an interface method as non-mandatory to implement | §5, §12 |
| `@operator(...)` | Overloads `[]`, `[]=`, `&[]`, `len`, and other operators — see below for `@operator_s`/`@operator_r`, which extend this | §7 |
| `@pure` | Asserts a function or call doesn't touch globals, for optimizer trust | §7, §10 |
| `@feat(...)` | Top-level feature-flag gating, combined with `& | !` | §10 |
| `@if(...)` | Per-instantiation conditional inclusion inside a generic, based on the generic's own parameters | §10 |
| `@inline` / `@noinline` | Suggests or forces inlining a function or a specific call; `@noinline` is the hard opposite | §1 |
| `@simd` | Pins a vector type to the platform's native C SIMD layout, for C interop | §8 |
| `@test` | Marks a function, or every function in a module section, as test-only | §13 |
| `@benchmark` | Marks a function as benchmark-only, excluded from ordinary compilation | §13 |
| `@private` | Visible only within the same module | §10 (the `func1`/`func2` dispatch example) |
| `@deprecated` | Marks a declaration deprecated, triggering a use warning | §11 (`FixedThreadPool`) |

### Visibility

Three attributes control where a declaration is visible from, and they're mutually exclusive:

| Attribute | Visible from |
|---|---|
| `@local` | Only the current module *section* (the specific `module foo;` block a declaration sits under, not the whole file if the file has multiple sections) |
| `@private` | The same module, across every section, but not from other modules |
| `@public` | Any module that imports this one — this is the default if nothing is specified |

```c3
module foo;
fn void ab_private() @private { ... }   // visible throughout module foo, not outside it
fn void ab_public() @public { ... }      // visible to importers too (redundant — this is default)
```

`@local` is the tightest of the three and is a genuinely different scope than `@private` — a large module split across several `module foo @private;` / `module foo;` sections can have declarations that are private to one specific section and invisible even to the rest of the same module, which `@local` is for.

### Linkage, Naming, and Export

These control how a declaration crosses the C ABI boundary or a library boundary — directly relevant to §1's C-interop story, since this is the mechanism underneath it:

```c3
extern fn int *ABC(void *x) @cname("ABC");   // C3-legal name, real external name is ABC
fn void my_lib_fn() @export("mylib_fn");      // exported from a static/dynamic library as "mylib_fn"
fn void internal_only() @nostrip;               // never stripped, even if apparently unused
```

| Attribute | Purpose |
|---|---|
| `@cname(name)` | Sets the external (linkage) name of a function, global, const, enum, union, struct, or `faultdef`. This is how a C3-legal identifier binds to a C symbol that doesn't follow C3's naming rules (§2) — necessary for wrapping C libraries whose names don't start with a lowercase letter, or that use characters C3 doesn't permit. |
| `@export(name?)` | Marks a declaration as exported: never stripped, and exposed as public when linking a static or dynamic library. Takes an optional string for the external name, equivalent to also adding `@cname`. Distinct from `@cname` alone — `@cname` only renames, `@export` additionally guarantees the symbol survives and is public. |
| `@extern` | Declares a function or global as linked in later — no body for a function, no init expression for a global. This is what `extern fn` actually is under the hood. |
| `@weak` | Emits a weak symbol, but if a non-weak definition of the same thing appears in the same compilation, the non-weak one wins. |
| `@weaklink` | Also emits a weak symbol, without the "non-weak wins" preference — a plain weak reference. |
| `@link(cond, lib1, lib2, ...)` | Implicitly links the named libraries when this symbol is used. On a module section, it applies transitively to every symbol in that section. |
| `@builtin` | Lets a macro, function, global, or constant be referenced from another module without the module-path prefix (bypassing the `::` qualification §2 otherwise requires). Meant to be used sparingly — it's an exception to the namespacing story, not a normal tool. |
| `@nostrip` | Prevents a declaration — and transitively, anything it depends on — from being stripped from the final binary even if nothing visibly calls it. |
| `@section(name)` | Places a global variable or function in a specific linker section. |
| `@obfuscate` | Strips identifying string values (names) from a declaration — used mostly on `faultdef` and `enum` members, where the name itself might otherwise leak into the binary. |

### Startup, Shutdown, and Calling Convention

```c3
fn void register_handlers() @init(256) { ... }   // runs before main; lower priority runs earlier
fn void flush_logs() @finalizer { ... }            // best-effort run at shutdown

extern fn void win32_call() @callconv("stdcall");   // only meaningful on 32-bit Windows targets
```

| Attribute | Purpose |
|---|---|
| `@init(priority?)` | Runs a `void`, no-argument function at startup, before `main`. Priority is 1–65535, lower runs earlier; values below 128 are reserved for the runtime's own initialization and shouldn't generally be used. |
| `@finalizer(priority?)` | The shutdown-time mirror of `@init`, same signature restriction, same priority scale. Because normal process termination doesn't always run finalizers cleanly (abnormal termination, `_exit`-style calls), this is a best-effort mechanism — not a guaranteed-to-run destructor. |
| `@callconv("cdecl" | "stdcall" | "veccall")` | Sets the calling convention for a function; ignored on targets where it doesn't apply. Functions default to `"cdecl"`, the standard C convention. `"stdcall"` matters only on 32-bit Windows — it's a no-op on 64-bit Windows even though many Win32 C headers still tag functions with it out of habit. |
| `@winmain` | Only legal on `main`. On Windows, generates a `WinMain` entry point that calls through to `main`, which unlocks other Windows-specific `main`-argument behavior; recommended for Windows GUI applications. Ignored (harmlessly) on every other target. |
| `@wasm(module?, name?)` | With zero or one argument, behaves like `@export` for non-`extern` symbols or `@cname` for `extern` ones. With two arguments (module name, then symbol name), it names the WASM import/export explicitly — only legal on `extern` symbols in that form. |

### `@operator_s` and `@operator_r` — Extending `@operator` to Mixed-Type Arithmetic

§7 already covers `@operator` for `[]`/`[]=`/`&[]`/`len` (the container-and-`foreach` use case). The same attribute family also drives arithmetic, bitwise, and equality overloading on user-defined types — and this is genuinely idiomatic C3 for anything vector- or numeric-type-shaped, not an edge case:

```c3
struct Vec2 { double x, y; }

fn Vec2 Vec2.add(self, Vec2 other) @operator(+) => { self.x + other.x, self.y + other.y };
fn Vec2 Vec2.scale(self, double k)  @operator(*) => { self.x * k, self.y * k };
```

`@operator` alone only covers `Vec2 + Vec2` or `Vec2 * double` — the receiver has to be the left-hand operand. It does **not** let you define `int + Vec2` or `double * Vec2`, because there's no receiver to hang the method off on the left. Two further attributes close that gap:

```c3
fn Vec2 Vec2.rscale(self, double k) @operator_s(*) => self.scale(k);   // k * self AND self * k both work
```

| Attribute | Effect |
|---|---|
| `@operator_s` | "Symmetric operator" — lets either operand come first; `k * v` and `v * k` both resolve to the same overload. |
| `@operator_r` | "Reverse operator" — specifically handles the case where the *other* type is the first term in the expression (asymmetric operations, like subtraction, where order matters and you can't just treat both orderings the same way `@operator_s` does). |

A few real rules worth knowing, since operator overloading is easy to misuse:

- Arithmetic overloads exist for `+ - * / %` and unary `-`; bit operators `^ | & << >>`; equality `== !=`; and the compound-assignment forms (`+= <<=` etc.) — but only user-defined types may be overloaded, and defining `==` automatically defines `!=` (and vice versa).
- If `+` is defined, `+=` is generated automatically from it — you don't have to write both, though you can explicitly override the compound form if there's a faster path than "compute the new value, then assign it."
- `Foo + int` and `Foo + double` can coexist as separate overloads. If you write `Foo + double` but not `Foo + int`, calling it with an `int` implicitly promotes to `double` through C3's normal numeric conversion rules (§1) — this is fine as long as exactly one overload matches after conversion; if multiple overloads become reachable through implicit conversion simultaneously, that's a compile-time ambiguity error, not a silent pick.
- Bitstructs already have `^ | &` defined structurally and may **not** have those specific three re-overloaded.
- The stdlib's own convention (worth following in your own overloads): an operator should behave the way it behaves on builtin types. `+` means addition, not concatenation; `<<` means left-shift, not "append" or "print." Overloading against that expectation is exactly the failure mode that makes people distrust operator overloading as a feature.

### Contract-Adjacent and Discard-Control Attributes

These interact with the Optional/contract machinery from §6 and §10 but aren't `@require`/`@ensure` themselves:

| Attribute | Purpose |
|---|---|
| `@nodiscard` | The return value may never be silently discarded — stronger than the default Optional-discard warning (§6), since it applies even to a non-Optional return. |
| `@maydiscard` | The opposite: explicitly permits discarding an Optional return without the `(void)` cast §6 otherwise expects. Meant to be rare — most of the stdlib's own Optional-returning functions want their failure noticed, not silently dropped. |
| `@noalias` | Applied to a pointer parameter; the equivalent of C's `restrict` — asserts the compiler doesn't need to worry about this pointer aliasing any other pointer parameter, which can unlock optimizations that would otherwise be unsafe in the presence of potential aliasing. |
| `@const` | On a macro: forces it to always compile-time-fold to a constant, erroring if it can't. A stricter, mandatory version of the "constant-foldable if called with constant arguments" behavior §10's `@fib` example relies on implicitly. |
| `@constinit` | On a `typedef` or `constdef`: allows the type to be initialized directly from a literal without an explicit cast — relevant to §4's `typedef` discussion, since ordinary `typedef`s require the explicit cast shown there. |
| `@format(n)` | Declares that a function or macro takes a format string at argument position `n` (zero-indexed) followed by format parameters, and turns on compile-time checking of those parameters against the format string — this is what makes a misuse of `io::printfn`-style functions a compile error rather than a runtime surprise. |
| `@safemacro` | Lets a macro drop the mandatory `@`-prefix from its declared name (§10) even in cases where the `#`-parameter or trailing-body rule would otherwise require it. |
| `@unused` | Marks a declaration as expectedly unused, suppressing the "declared but never used" warning without also matching `@used`'s stronger guarantee. |
| `@used` | The opposite signal: marks a parameter or value as one that *must* be used, an intentional constraint rather than a warning-suppressor. |
| `@reflect` | Adds extra reflection metadata to a declaration. Documented as currently having no observable effect — present for forward compatibility rather than doing anything today. |
| `@allow_deprecated` | Placed on a function, suppresses `@deprecated` warnings that would otherwise fire from that function's own parameters or body — useful for a shim that has to keep calling a deprecated API on purpose. |
| `@tag(name, value)` | Attaches an arbitrary compile-time tag to a type, function, member, or variable, retrievable later via reflection (`Foo::has_tag("bar")`, `Foo::get_tag("bar")`, or `$reflect(my_global).has_tag("bar")` for locals/members). This is the mechanism something like a serialization library would use to mark "this field renames to `x` in JSON" without baking that concept into the language itself. |

### Low-Level and Platform-Specific Attributes

These exist for kernel-, embedded-, or ABI-boundary-level work — not everyday application code, but real and occasionally load-bearing:

| Attribute | Purpose |
|---|---|
| `@naked` | Disables prologue/epilogue emission for a function; the body must be a raw `asm` statement. For hand-written assembly routines that manage their own stack frame. |
| `@noredzone` | Disables red-zone stack usage on targets that normally use one — required in contexts (interrupt handlers, signal handlers) where the red zone assumption can be violated by an async interruption. |
| `@nostackprobe` | Suppresses stack-probe emission where it would otherwise be inserted. |
| `@nostackprotector` | Suppresses stack-protection (canary) emission for a function where it would otherwise apply. |
| `@stackprobe("none" \| "call" \| "inline")` | Explicitly sets a function's stack-probe strategy. |
| `@stackprotector("none" \| "basic" \| "strong" \| "all")` | Explicitly sets a function's stack-protection level. |
| `@nosanitize` | Prevents sanitizers from instrumenting this specific function. |
| `@bigendian` / `@littleendian` | On a `bitstruct`, lays out the bits as though stored in the named endianness, regardless of the host's actual endianness — for parsing wire formats and file formats with a fixed, specified byte order. |
| `@overlap` | On a `bitstruct`, permits fields to declare overlapping bit ranges, which is otherwise rejected. |
| `@norecurse` | On an `import`, imports only the named module — not its sub-modules or parent modules — narrowing what a single `import` statement pulls in. |
| `@jump` | On a `switch` statement, forces it to compile as a guaranteed jump table rather than leaving the strategy to the compiler's own heuristics — a targeted optimization hint for switches where jump-table codegen is known to be faster than the compiler's default choice. |

### User-Defined Attributes: `attrdef`

Attribute *groups* are user-definable with `attrdef`, bundling several built-in attributes (optionally parameterized) under one name:

```c3
attrdef @HotPath = @inline, @nostrip;
attrdef @Renamed(name) = @cname(name);
attrdef @EmptyGroup;   // a legal, deliberately empty group

fn void critical_loop() @HotPath { ... }
// identical to:
fn void critical_loop_equivalent() @inline @nostrip { ... }

attrdef @JsonKey(val) = @tag("json_name", val);
struct Payload
{
    int user_id @JsonKey("userId");
}
$echo $reflect(Payload.user_id).get_tag("json_name");   // echoes "userId" at compile time
```

This is purely a naming/bundling convenience over existing attributes — `attrdef` cannot invent new compiler behavior, only group and parameterize what's already built in. It's the attribute-system equivalent of §10's macro sigils: a way to give a recurring combination of low-level knobs one memorable, intention-revealing name, rather than repeating the same four-attribute stack on every declaration that needs it.

