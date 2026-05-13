# C3 — C Interop

Load when calling C libraries from C3, exporting C-callable symbols, or working with weak / platform-conditional symbols.

---

## Declaring and calling C functions

```c3
// Declare C functions
extern fn int printf(char* format, ...);
extern fn void* malloc(sz size);
extern fn void  free(void* ptr);
extern fn int   strcmp(char* a, char* b);

// Pass fixed array to C function (& gets pointer to first element)
char[64] buf;
printf("%s\n", &buf);
```

Or import the `libc` module to get typed wrappers around the platform C runtime:

```c3
import libc;
libc::printf("Hello %s\n", "world");
void* p = libc::malloc(1024);
libc::free(p);
```

`libc` covers `printf`, `malloc`, `free`, `strlen`, `memcpy`, `stat`, etc.

---

## Exporting C-callable functions

```c3
fn int my_func(int x) @export @cname("my_c_func") { return x * 2; }
```

- `@export` — emit the symbol with C linkage
- `@cname("…")` — override the symbol name (otherwise C3-mangled)

---

## Weak symbols & platform-conditional definitions

```c3
fn void hook() @weak { }                              // multiple defs allowed; non-weak wins
fn void plat_init() @weaklink @if(env::LINUX) { }     // @weaklink affects only linkage
```

Combine `@weak` / `@weaklink` with `@if(env::OS)` for conditional platform stubs.

---

## Tips

- Fixed arrays don't decay to pointers automatically. Use `&fixed` to get an `int*`.
- C string literals from C3 are `String` (slice). Use `.ptr` to get the raw `char*`, or `string::tformat_zstr(…)` to get a `ZString`.
- For variadics that must reach a C va_list, see `std::core::cvarargs`.
