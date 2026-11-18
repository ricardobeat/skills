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
fn int my_func(int x) @export("my_c_func") { return x * 2; }
```

- `@export` keeps a symbol and gives it external visibility. `@export("name")` also sets its C name.
- `@cname("name")` sets the external C name without exporting the declaration. Platform decoration still applies, such as a leading underscore on macOS.
- `@asmname("name")` sets the exact assembly symbol with no platform decoration. Use it for assembly-defined or otherwise unconventional symbols; it cannot be used on generic declarations.

---

## Weak symbols & platform-conditional definitions

```c3
fn void hook() @weak { }                              // multiple defs allowed; non-weak wins
fn void plat_init() @weaklink @feat(LINUX) { }        // @weaklink affects only linkage
```

Combine `@weak` / `@weaklink` with `@feat(OS)` for conditional platform stubs. `@feat` takes a feature list such as `LINUX`, `DARWIN`, `POSIX | !WIN32`, or `POSIX & BIG_ENDIAN`, not an `env::` expression.

---

## Linking and ABI

- `@link("foo")` on a module or declaration adds a native library dependency when the symbol is used. Otherwise add `-l foo` on the command line or `"linked-libraries": ["foo"]` to `project.json`.
- C headers use fixed-width assumptions that do not always match C3: use `CInt`, `CUInt`, `CLong`, `CULong`, and friends from `std::core::cinterop` for exact C integer widths.
- C enums are `CInt`-sized; C bitfields need a manually matched C3 `bitstruct`. `@packed`, `@compact`, `@align`, `@bigendian`, and `@littleendian` control layout where needed.
- Slices are pointer-plus-length values, not C pointers. Pass `slice.ptr` and `slice.len` separately unless the C API defines a compatible struct.

---

## Tips

- Fixed arrays don't decay to pointers automatically. Use `&fixed`; a pointer to the array converts implicitly to a pointer to its first element. For a C parameter declared as `int a[4]`, use `int*` in the `extern fn` declaration, not `int[4]`.
- `String` is a byte slice. Its `.ptr` is not necessarily NUL-terminated, especially after slicing, splitting, or loading a file. Use `s.zstr_copy(mem)` or `s.zstr_tcopy()` inside an allocator scope before passing it to a C API expecting a C string. `ZString` is a pointer to NUL-terminated bytes.
