# C3 Standard Library Reference (0.8.0)

Curated index of the most useful APIs in the C3 stdlib. For exhaustive lists, browse [github.com/c3lang/c3c/tree/v0.8.0/lib/std](https://github.com/c3lang/c3c/tree/v0.8.0/lib/std).

**Conventions used below:**
- `T?` is an Optional (may carry a fault). Always handle with `!`, `??`, `!!`, or `if (catch …)`.
- `t*` prefix = temporary-allocator variant (uses `tmem`, freed at `@pool()` exit).
- Method receivers: `(&self, …)` means pointer receiver (mutating).
- `Allocator` is the standard allocator interface — pass `mem` (heap) or `tmem` (temp).

---

## Built-ins (`@builtin`, no import needed)

Always in scope, even without `import std::core::…`:

```c3
// Allocation
mem::new(T, .field = v)   mem::tnew(T)               // single value
mem::new_array(T, n)      mem::temp_array(T, n)      // zero-init array
mem::alloc(T)             mem::talloc(T)             // single value (no init)
mem::alloc_array(T, n)    mem::talloc_array(T, n)    // uninitialized array
mem::free(p)              mem::tmalloc(size)         // raw alloc
@clone(v) / @tclone(v)    @clone_slice(s) / @tclone_slice(s)

// Faults that any code may produce
NO_MORE_ELEMENT  NOT_FOUND  TYPE_MISMATCH  CAPACITY_EXCEEDED  NOT_IMPLEMENTED  TIMEOUT

// Macros / control
@swap(a, b)               @scope(var; @body)         // capture and restore
@addr(val)                @typeid(value)             @ok(e)  @catch(e)
@try(v, expr)             @try_catch(v, expr, FAULT)
always_assert(cond, fmt, …)   unreachable("…")   unsupported("…")   abort("…")
@likely(cond) / @unlikely(cond) / @expect(value, expected)
@prefetch(ptr, VERY_NEAR | NEAR | FAR | VERY_FAR, $write=false)
bitcast(expr, $Type)      anycast(any_val, $Type)    enum_by_name($Enum, "NAME")
breakpoint()              @syscall(...)              @rnd()

// Compile-time string ops
@str_upper($s)  @str_lower($s)  @str_pascalcase($s)  @str_snakecase($s)
@str_camelcase($s)  @str_constantcase($s)  @str_capitalize($s)  @str_uncapitalize($s)
@str_replace($s, $pat, $repl, $limit=0)  @str_hash($s)  @str_find($s, $needle)

// Hash a primitive (works on all int types, vectors, arrays, String, ZString, char[])
v.hash()
```

---

## `std::io` — Input/output

```c3
// stdout / stderr (newline variants append \n)
io::print(value)         io::printn(value)
io::printf(fmt, …)       io::printfn(fmt, …)
io::eprint(value)        io::eprintn(value)
io::eprintf(fmt, …)      io::eprintfn(fmt, …)
io::putchar(c)
io::bprintf(buffer, fmt, …)    // print into a char[] buffer

// Stream handles
File* io::stdout()   File* io::stderr()   File* io::stdin()

// Read a line (allocating)
String? io::readline(Allocator alloc, stream = io::stdin(), sz limit = 0)
String? io::treadline(stream = io::stdin(), sz limit = 0)

// Generic stream print
sz? io::fprint(out, value)
sz? io::fprintf(out, fmt, …)
sz? io::fprintfn(out, fmt, …)
sz? io::fprintn(out, value = "")

// Stream interfaces (your structs can implement these)
interface InStream  { fn char? read_byte();  fn sz? read(char[] buf); … }
interface OutStream { fn void? write_byte(char c);  fn sz? write(char[] data); … }

// Format string: %s, %d, %x, %X, %o, %b, %f, %g, %e, %c, %p, %h
// No width-type qualifiers (no %lld/%u/%zu) — %d handles all integer widths.
```

### `std::io::file`

```c3
File? file::open(String filename, String mode)        // modes: "r","w","rb","wb","r+","a", …
File? file::open_path(Path path, String mode)
File  file::from_handle(CFile c_file)
bool  file::exists(String path)
bool  file::is_file(String path)        bool file::is_dir(String path)
long? file::get_size(String path)       Time? file::last_modified(String path)
void? file::delete(String path)

// Whole-file convenience
char[]? file::load(Allocator alloc, String filename)
char[]? file::load_temp(String filename)
char[]? file::load_buffer(String filename, char[] buffer)
void?   file::save(String filename, char[] data)

// File methods (a File acts as InStream + OutStream)
f.read(buffer)        f.write(buffer)        f.read_byte()       f.write_byte(c)
f.seek(offset, FROM_START | FROM_CURSOR | FROM_END)
f.cursor()            f.size()               f.eof()             f.flush()
f.close()             f.isatty()             f.fd()              f.memopen(data, mode)
```

### `std::io::path`

In 0.8.0 `Path` is `PathPosix` or `PathWin` depending on the platform. It implicitly casts to `String`.

```c3
Path? path::new(Allocator alloc, String s)     Path? path::tnew(String s)
Path? path::cwd(Allocator alloc)               Path? path::tcwd()
void? path::chdir(path)

Path? path::home_directory(Allocator)          Path? path::temp_directory(Allocator)
Path? path::desktop_directory(Allocator)       Path? path::documents_directory(Allocator)
Path? path::downloads_directory(Allocator)     Path? path::pictures_directory(Allocator)
// Also: videos, music, screenshots, saved_games, templates, public_share

bool  path::is_dir(p)      bool path::is_file(p)
bool  path::exists(p)      long? path::file_size(p)
void? path::delete(p)      bool? path::mkdir(p, bool recursive=false, perm=NORMAL)
bool? path::rmdir(p)       void? path::rmtree(p)
PathList? path::ls(Allocator, Path dir, bool no_dirs=false, bool no_symlinks=false, String mask="")

// Methods (Path is convertable to String)
p.append(alloc, ...parts, extension="")     // multi-part / extension
```

---

## `std::collections` — Containers

All containers come in two init flavors: `.init(alloc, ...)` heap, `.tinit(...)` temp. All take a `Type` (or `Key`/`Value`) generic parameter — instantiate with `alias MyList = List{int};`.

### `List{T}` — dynamic array
```c3
List{int} l;
l.init(mem, initial_capacity = 16);   // or l.tinit(16) for temp allocator
l.push(v)    l.push_front(v)    l.push_all(arr)    l.insert_at(idx, v)
l.pop()      l.pop_first()      l.remove_at(idx)   l.remove_unordered_at(idx)
l.remove_first()  l.remove_last()  l.clear()       l.reverse()  l.swap(i, j)
l.first()    l.last()           l.get(idx)         l.set(idx, v)
l.len()      l.is_empty()       l.contains(v)      l.index_of(v)   l.rindex_of(v)
l.to_array(alloc)   l.to_tarray()   l.array_view()  // slice over storage
l.remove_if(predicate)            l.retain_if(predicate)
l.remove_using_test(test_fn, ctx) l.retain_using_test(test_fn, ctx)
l.add_all(&other)   l.reserve(extra)   l.free()
// Operators: l[i]  l[i] = v  len(l)  &l[i]
```

### `FixedList{T, SIZE}` — stack-allocated fixed-cap list. Same API as `List` plus `push_try()`, `push_all_to_limit()`.

### `HashMap{K, V}` — open-addressed hash map
```c3
HashMap{String, int} m;
m.init(mem, capacity = 16, load_factor = 0.75);   // m.tinit(...) for temp
m.set(key, val)             m.get(key)            // optional V?
m.has_key(key)              m.remove(key)
m.get_ref(key)              m.get_or_create_ref(key)    // for in-place mutation
m.@get_or_set(key, default_expr)                  // returns existing OR sets+returns default
m.keys(alloc) / m.tkeys()   m.values(alloc) / m.tvalues()
m.iter()  m.key_iter()  m.value_iter()            // foreach-compatible
m.@each(; |k, v| { ... })   m.@each_entry(; |entry| { ... })
m.len()  m.is_empty()  m.clear()  m.free()
// Operators: m[k]  m[k] = v  &m[k]
```

### `HashSet{T}`
```c3
HashSet{int} s;   s.init(mem);
s.add(v)    s.add_all(arr)    s.contains(v)    s.remove(v)    s.len()
s.set_union(alloc, &other)         s.intersection(alloc, &other)
s.difference(alloc, &other)        s.symmetric_difference(alloc, &other)
s.is_subset(&other)                s.iter()
```

### `SortedMap{K, V}` — skip-list ordered map (new in 0.8.0)
```c3
SortedMap{int, String} m;   m.init(mem);
m.set(k, v)   m.get(k)   m.remove(k)   m.has_key(k)
m.first_key() / m.last_key()      m.pop_first() / m.pop_last()
m.floor_key(k)   m.ceiling_key(k)   m.lower_key(k)   m.higher_key(k)
m.iter()   m.iter_from(k)   m.iter_range(from, to)
m.clone(alloc)   m.merge(&other)
```

### `Deque{T}`, `LinkedList{T}`, `RingBuffer{T, N}`
```c3
// Deque (double-ended growable)
d.push(v)  d.push_front(v)  d.pop()  d.pop_first()  d.first() / d.last()
d.get(i)   d.set(i, v)      d.reserve(extra)  d.shrink()  d.normalize()
d.pop_into(slice)  d.pop_first_into(slice)
// RingBuffer — fixed-cap circular; push, pop_first, first, last, get, set
```

### `PriorityQueue{T}` / `PriorityQueueMax{T}`
```c3
PriorityQueue{int} q;   q.init(mem);
q.push(v)   q.pop()    q.first()    q.remove_at(idx)   q.len()
```

### `BitSet{SIZE}` / `GrowableBitSet{T}`
```c3
BitSet{1024} b;
b.set(i)   b.unset(i)   b.get(i)   b.set_bool(i, v)   b.cardinality()
b.or(other) / b.and(other) / b.xor(other)    // operators: | & ^ |= &= ^=
```

### `Maybe{T}`, `Pair{A, B}`, `Triple{A, B, C}`, `Range{T}`, `ExclusiveRange{T}`

---

## `std::core::string`

```c3
// Types
typedef String  = inline char[];      // string slice
typedef ZString = inline char*;       // C-style NUL-terminated
typedef WString = inline Char16*;     // UTF-16 NUL-terminated

// Formatting (allocate-and-return)
String string::format(Allocator, fmt, …)        String string::tformat(fmt, …)
String string::bformat(char[] buffer, fmt, …)   // format into a fixed buffer
ZString string::tformat_zstr(fmt, …)

// Joins
String string::join(Allocator, String[] parts, String joiner)
String string::tjoin(String[] parts, String joiner)

// Methods on String (s is a String)
s.copy(alloc)              s.tcopy()
s.concat(alloc, other)     s.tconcat(other)
s.replace(alloc, needle, repl)    s.treplace(needle, repl)
s.split(alloc, delim, max=0, skip_empty=false)    s.tsplit(delim)
s.split_to_buffer(delim, buffer, max, skip_empty)?  // no alloc, into existing slice

s.trim(chars = " \n\t\r\f\v")    s.trim_left(chars)    s.trim_right(chars)
s.trim_charset(ascii_charset)
s.strip_prefix(prefix)     s.strip_suffix(suffix)   // 0.8.0 (was strip / strip_end)
s.starts_with(p)           s.ends_with(p)
s.contains(sub)            s.contains_char(c)
s.index_of(sub)            s.rindex_of(sub)
s.index_of_char(c)         s.index_of_char_from(c, start)   s.rindex_of_char(c)
s.index_of_chars(char_slice)
s.count(sub)               s.compare_to(other)       s.compare_to_ignore_case(other)
s.to_lower(alloc) / s.tlower()    s.to_upper(alloc) / s.tupper()
s.zstr_copy(alloc)         s.zstr_tcopy()
s.hash()                   s.free(alloc)

// ZString methods
zs.str_view()              zs.char_len()        zs.len()        zs == other (.eq)

// Parsing into integers / floats (find on `int.parse`, `long.parse`, `float.parse`, etc.)
int? int::parse(s, int radix = 10)        // 0.8.0: stdlib offers parse() helpers per type
```

### `std::core::dstring` — DString (dynamic, mutable string)

```c3
DString d = dstring::new(mem, "hi");           // or dstring::new_with_capacity(mem, 64)
DString d2 = dstring::temp("hi");              // temp; auto-freed at @pool()

d.append("hello")    d.append_char(' ')    d.append_char32(U'😀')
d.append_string(s)   d.append_dstring(other) d.append_bytes(byte_slice)
d.append_char_repeat('-', 10)   d.append_string_repeat("ab", 3)
d.appendf("%s = %d", "x", 42)   d.appendfn(fmt, …)        // with newline
d.insert_at(idx, value)         d.insert_chars_at(idx, "…")  d.insert_char_at(idx, c)
d.replace(needle, repl)         d.replace_char(c, c2)
d.delete(start, len = 1)        d.delete_range(start, end)
d.chop(new_len)                 d.clear()
d.str_view()                    d.zstr_view()
d.copy(alloc) / d.tcopy()       d.copy_str(alloc) / d.tcopy_str()
d.copy_zstr(alloc) / d.zstr_view()
d.reverse()                     d.reserve(extra)
d.len()                         d.capacity()                d.free()
d.read_from_stream(in_stream)?  d.write(buf)?   d.write_byte(c)?
// Operators: d[i]  d[i] = c  len(d)  &d[i]
```

### `std::core::ascii`

`is_lower/upper/digit/bdigit/odigit/xdigit/alpha/print/graph/space/alnum/punct/blank/cntrl(c)`,
`to_lower(c)`, `to_upper(c)`. Same names as `@`-macro forms and as char methods (`c.is_alpha()`).

Sets (`AsciiCharset` = bitmap of ASCII): `WHITESPACE_SET`, `NUMBER_SET`, `ALPHA_SET`, `ALPHA_UPPER_SET`, `ALPHA_LOWER_SET`, `ALPHANUMERIC_SET`. Build your own with `ascii::@create_set("0xABCDEFabcdef")` (compile-time) or `ascii::create_set(…)`.

---

## `std::core::mem`

```c3
// Faults
mem::OUT_OF_MEMORY      mem::INVALID_ALLOC_SIZE

// Constants
mem::KB  mem::MB  mem::GB  mem::TB             // byte sizes
mem::DEFAULT_MEM_ALIGNMENT                     // platform default
mem::os_pagesize()

// Raw allocators (all `@builtin`)
mem::malloc(size)        mem::malloc_aligned(size, align)
mem::calloc(size)        mem::calloc_aligned(size, align)
mem::realloc(p, size)    mem::realloc_aligned(p, size, align)
mem::free(p)             mem::free_aligned(p)
mem::tmalloc(size)       mem::tcalloc(size)    mem::trealloc(p, size)

// Typed allocation macros
mem::new(T, .field = v)             mem::new_aligned(T)         mem::tnew(T)
mem::alloc(T)                       mem::alloc_aligned(T)       mem::talloc(T)
mem::new_array(T, n)                mem::alloc_array(T, n)
mem::temp_array(T, n)               mem::talloc_array(T, n)

// Memory ops
mem::copy(dst, src, n)           mem::move(dst, src, n)
mem::clear(dst, n)               mem::set(dst, byte, n)
mem::zero_volatile(slice)        mem::equals(a, b, n = -1)

// Atomics (free functions)
mem::compare_exchange(&p, old, new, ordering = SEQ_CONSISTENT)
@atomic_load(x, ordering)        @atomic_store(x, val, ordering)
// Ordering: RELAXED | ACQUIRE | RELEASE | ACQUIRE_RELEASE | SEQ_CONSISTENT

// Volatile / unaligned access
@volatile_load(x)                @volatile_store(x, v)
@unaligned_load(p, $align)       @unaligned_store(p, v, $align)
// Type wrappers:
Volatile{int} v;     v.set(5);     int x = v.get();
UnalignedRef{int} u;

// Temp allocator (arena)
@pool(sz reserve = 0; |...| { ... });             // create + free at scope exit
mem::@scoped(allocator; |...| { ... })            // make `mem` reference allocator
mem::@stack_mem(2048; |Allocator m| { ... })      // arena on stack
mem::@stack_pool(2048; |...| { ... })             // stack-based @pool

// Leak detection
mem::@assert_leak(report = true; |...| { ... })   // panic if any allocs leak
mem::@report_heap_allocs_in_scope(enabled = true; |...| { ... })
```

---

## `std::core::env` — Build-time constants

```c3
env::OS_TYPE     env::ARCH_TYPE                  // enums (LINUX, DARWIN, WIN32, X86_64, AARCH64, …)
env::LINUX  env::DARWIN  env::WIN32  env::POSIX  env::BSD_FAMILY
env::FREEBSD  env::OPENBSD  env::NETBSD  env::ANDROID  env::EMSCRIPTEN
env::WASM   env::WASI    env::FREESTANDING_PE32  env::FREESTANDING_ELF
env::ARCH_64_BIT   env::ARCH_32_BIT   env::BIG_ENDIAN
env::LIBC   env::NO_LIBC   env::CUSTOM_LIBC
env::COMPILER_OPT_LEVEL    env::COMPILER_SAFE_MODE   env::DEBUG_SYMBOLS
env::BENCHMARKING   env::TESTING   env::PANIC_MSG   env::BACKTRACE
env::I128_NATIVE_SUPPORT   env::F16_SUPPORT   env::F128_SUPPORT
env::ADDRESS_SANITIZER   env::MEMORY_SANITIZER   env::THREAD_SANITIZER
env::COMPILER_BUILD_HASH   env::COMPILER_BUILD_DATE   env::LLVM_VERSION
env::NATIVE_THREADING   env::NATIVE_STACKTRACE   env::HAS_NATIVE_ERRNO
env::AUTHORS   env::AUTHOR_EMAILS   env::PROJECT_VERSION
```

Use in `@if(env::WIN32)`, `$if env::ARCH_64_BIT:`, etc.

---

## `std::core::array`

Functional helpers — most are macros, work on any array-like:

```c3
array::contains(arr, v)           array::index_of(arr, v)         array::rindex_of(arr, v)
array::concat(alloc, a, b)        array::tconcat(a, b)
array::@reduce(arr, identity, |a, b| a + b)
array::@sum(arr)                  array::@product(arr)
array::@filter(alloc, arr, |x| x > 0)        array::@tfilter(arr, |x| ...)
array::@indices_of(alloc, arr, |x| ...)      array::@tindices_of(arr, |x| ...)
array::@any(arr, |x| ...)         array::@all(arr, |x| ...)
array::even(alloc, arr)           array::odd(alloc, arr)
array::unlace(alloc, arr, &left, &right)
array::@zip(alloc, a, b, |x,y| op, fill_with = …)    array::@tzip(...)
array::@zip_into(left, right, |a, b| op)
array::slice2d(&arr, x = 0, xlen = 0, y = 0, ylen = 0)
```

---

## `std::core::conv` — Unicode

```c3
conv::detect_bom(input)              // UnicodeBom enum
conv::utf8_codepoints(s)             // number of codepoints in a UTF-8 String
conv::utf8_to_char32(ptr, &size)?    Char32? from UTF-8
conv::char32_to_utf8(c, output)?     conv::char32_to_utf8_unsafe(c, &out_ptr)

// Conversions between UTF-8, UTF-16, UTF-32 (suffix `_unsafe` for unchecked)
conv::utf32to8(in, buf)?      conv::utf8to32(in, buf)?
conv::utf16to8_unsafe(in, buf, $unaligned, $byteswap)?
conv::utf8to16_unsafe(in, buf)?  conv::utf8to32_unsafe(in, buf)?
conv::utf32to8_unsafe(in, buf, $unaligned, $byteswap)
// Length helpers
conv::utf8len_for_utf16(s)   conv::utf8len_for_utf32(s)
conv::utf16len_for_utf8(s)   conv::utf16len_for_utf32(s)
```

---

## `std::math`

```c3
// Constants (0.8.0 names)
math::PI        math::HALF_PI       math::QUARTER_PI      math::INV_PI
math::TWO_OVER_PI    math::TWO_OVER_SQRT_PI
math::E         math::LOG2E         math::LOG10E
math::LN2       math::LN10          math::SQRT2          math::INV_SQRT2
math::FLOAT_MAX / FLOAT_MIN / FLOAT_DENORM_MIN / FLOAT_EPSILON
math::HALF_MAX / HALF_MIN / HALF_EPSILON …  (same for double/float128/bfloat16)

// Trig / exponential / power (operate on float, double, float128, vectors)
math::sin(x)   math::cos(x)   math::tan(x)   math::asin(x)   math::acos(x)   math::atan(x)
math::atan2(y, x)
math::sinh(x)  math::cosh(x)  math::tanh(x)  math::asinh(x)  math::acosh(x)  math::atanh(x)
math::csc(x)   math::sec(x)   math::cot(x)    // 0.8.0 (renamed from cosec, cotan)
math::exp(x)   math::exp2(x)  math::exp10(x)
math::log(x, base)             math::log2(x)   math::log10(x)   math::ln(x)
math::pow(x, y)   math::sqrt(x)   math::cbrt(x)   math::hypot(a, b)

// Numeric
math::abs(x)   math::sign(x)   math::clamp(x, lo, hi)
math::min(a, b, …)   math::max(a, b, …)
math::ceil(x)  math::floor(x)  math::round(x)   math::trunc(x)
math::fmod(x, y)  math::mad(a, b, c)            // 0.8.0 (renamed muladd → mad)
math::lerp(a, b, t)   math::lerp_smooth(a, b, t)
math::deg_to_rad(x)   math::rad_to_deg(x)
```

### `std::math::random`

```c3
// Default-seeded global helpers
math::srand(seed)        math::rand(range)        math::rand_in_range(min, max)
math::rnd()              // double in [0, 1)

// Generators (Sfc64Random is default; also: Sfc32Random, Pcg32Random, Mt19937Random, ChaCha20Random, …)
DefaultRandom r;
random::seed(&r, 42)        random::seed_entropy(&r)
random::next(&r, range)     random::next_in_range(&r, min, max)
random::next_bool(&r)       random::next_float(&r)   random::next_double(&r)
```

### `std::math::vector`

```c3
// Predefined aliases (use C3 vector type T[<N>])
alias Vec2 = float[<2>];    Vec3 = float[<3>];   Vec4 = float[<4>];
// And: int[<N>], double[<N>], long[<N>] vectors are first-class.

v.length()       v.length_sq()      v.normalize()      v.distance(other)
v.dot(other)     v.cross(other)     v.angle(other)
v.rotate(angle)  v.transform(mat4)  v.refract(n, r)
v.lerp(other, t)        v.barycentric(a, b, c)
v.project(model, proj, viewport)        v.unproject(...)
```

### Other math: `bigint`, `complex`, `matrix` (`Matrix2/3/4`, `Matrix2f/3f/4f`), `quaternion` (`Quaternionf`), `distributions`, `easing`, `shapes`, `uuid`.

---

## `std::time`

```c3
// Duration / time constants (all in microseconds)
time::US time::MS time::SEC time::MIN time::HOUR time::DAY time::WEEK time::MONTH time::YEAR
time::DURATION_ZERO   time::FAR_FUTURE   time::FAR_PAST

// Helpers to build a Duration
time::us(n)  time::ms(n)  time::sec(n)  time::min(n)  time::hour(n)  time::day(n)

// Time / Duration / NanoDuration
Time t = time::now();         // wall clock (microseconds since epoch)
Duration d = t1 - t0;         // arithmetic on Time values returns Duration
t.add_seconds(n)  t.diff_hours(other)  …

// DateTime
DateTime dt = datetime::now();
DateTime at = datetime::at(year, month=JANUARY, day=1, hour=0, min=0, sec=0, us=0);
TzDateTime tz = datetime::at_tz(year, ..., gmt_offset = 0);
dt.set(year, month, day, hour, min, sec, us)
dt.add_seconds/minutes/hours/days/weeks/months/years(n)
dt.to_local()  dt.to_gmt_offset(offset)  dt.with_gmt_offset(offset)
dt.year / dt.month / dt.day / dt.hour / dt.min / dt.sec / dt.us / dt.weekday

// Format
String DateTime.format_rfc3339(self, Allocator)    // also tformat_rfc3339
String DateTime.format(self, Allocator, String fmt)

// Monotonic clock (for timing)
Clock c = clock::now();
NanoDuration elapsed = c.mark();      // restart + return time since last mark
NanoDuration since = c.to_now();      // peek without restart
```

---

## `std::os`

```c3
// Process control
os::exit(int code) @noreturn
os::fastexit(int code) @noreturn

// Spawn child processes
Process? os::process::spawn(String[] argv, SpawnOptions opts = {}, String[] env = {})
int?     os::process::run(String[] argv, SpawnOptions opts = {}, String[] env = {})
String?  os::process::run_capture_stdout(char[] buf, String[] argv, SpawnOptions opts = {}, String[] env = {})

// Process methods
p.join()           CInt? exit code
p.terminate()      // kill child
p.destroy()
p.stdout() / p.stderr()  → File
p.read_stdout(buf, size)    p.read_stderr(buf, size)
```

### `std::os::env`

```c3
String? os::env::get_var(Allocator, name)        String? os::env::tget_var(name)
bool    os::env::set_var(name, value, overwrite = true)
bool    os::env::clear_var(name)
String? os::env::get_home_dir(Allocator)
Path?   os::env::get_config_dir(Allocator)
String? os::env::executable_path()
```

### `std::os::backtrace` — `os::backtrace::capture(buf)`, `os::backtrace::resolve(...)`.

---

## `std::net` — Networking

```c3
// TCP
TcpSocket?       net::tcp::connect(String host, int port, Duration timeout = 0, SocketOption…)
TcpSocket?       net::tcp::connect_async(String host, int port, SocketOption…)
TcpServerSocket? net::tcp::listen(String host, int port, int backlog, SocketOption…)
TcpSocket?       net::tcp::accept(TcpServerSocket* server)
TcpSocketPair?   tcp::TcpSocketPair.init(&self)             // socket pair

// UDP
UdpSocket? net::udp::connect(String host, int port, SocketOption…)
UdpSocket? net::udp::connect_async(String host, int port, SocketOption…)

// Common socket operations (TcpSocket / UdpSocket implement InStream + OutStream)
s.read(buf)        s.write(buf)
s.close()          s.set_option(opt, val)   s.get_*  (broadcast, keepalive, reuseaddr, …)
s.set_send_timeout(ms)     s.set_recv_timeout(ms)
s.peer_address()           s.local_address()

// Poll
Poll[] polls = { { .socket = fd, .events = READ | WRITE } };
ulong? net::poll(Poll[] polls, Duration timeout)
ulong? net::poll_ms(Poll[] polls, long timeout_ms)
net::POLL_FOREVER

// InetAddress
InetAddress? net::inetaddr::ipv4_from_str(s)        InetAddress? net::inetaddr::ipv6_from_str(s)
addr.is_loopback() / .is_multicast() / .is_link_local() / .is_site_local() / .is_any_local()
addr.to_string(alloc) / addr.to_tstring()
// IpProtocol enum: V4, V6, UNSPECIFIED

// URL
Url? net::url::parse(Allocator, s)          Url? net::url::tparse(s)
UrlQueryValues net::url::parse_query(Allocator, query_string)
String url.to_string(alloc)
qv.add(key, value)         qv.free()
```

---

## `std::threads`

```c3
// Threads (NativeThread)
Thread t;     t.create(&worker_fn, arg)?    t.join()?    t.detach()?
Thread::current_id()        // current OS thread id
thread::sleep(Duration d)
thread::yield()
thread::set_priority(prio)  thread::set_stack_size(bytes)

// Mutexes (initialize before use)
Mutex m;   m.init()?     m.lock()?    m.unlock()    m.try_lock()    m.destroy()
RecursiveMutex rm;          rm.init()?
TimedMutex tm;              tm.init()?    tm.timeout_lock(Duration)?
TimedRecursiveMutex trm;    trm.init()?

// Condition variables
ConditionVariable cv;       cv.init()?    cv.wait(&m)?    cv.signal()    cv.broadcast()
cv.timeout_wait(&m, Duration)?

// Once-init
Once o;        o.call(&init_fn)

// Channels (0.8.0: pointer-typed)
BufferedChannel{int}*   bc = channel::create_buffered{int}(mem, capacity = 16);
UnbufferedChannel{int}* uc = channel::create_unbuffered{int}(mem);
OneShotChannel{int}     oc;       // 0.8.0 new
bc.send(v)?    bc.recv()?       bc.close()
oc.send(v)?    oc.recv()?

// Thread pool
ThreadPool tp;              tp.init(ThreadSettings{ .thread_count = 4 })?
tp.push(&task_fn, arg)      tp.join()    tp.destroy()    tp.stop_and_destroy()
```

---

## `std::atomic` — `Atomic{T}`

```c3
Atomic{int} a;
a.load(SEQ_CONSISTENT)       a.store(5, SEQ_CONSISTENT)
a.add(1)   a.sub(1)   a.mul(2)   a.div(2)   a.max(5)   a.min(5)
a.or(0xFF)   a.and(mask)   a.xor(mask)   a.shr(2)   a.shl(2)
Atomic{bool} b;       b.set()    b.clear()        // test-and-set / clear

// Plain-pointer atomics
atomic::fetch_add(&x, 1)     atomic::fetch_sub(&x, 1)     atomic::fetch_or(&x, m)
atomic::fetch_and(&x, m)     atomic::fetch_xor(&x, m)
atomic::flag_set(&b)         atomic::flag_clear(&b)
atomic::fetch_max(&x, v)     atomic::fetch_min(&x, v)
// Orderings: RELAXED, CONSUME, ACQUIRE, RELEASE, ACQUIRE_RELEASE, SEQ_CONSISTENT
```

---

## `std::sort`

```c3
sort::quicksort(array)             sort::quicksort(array, cmp_fn)
sort::mergesort(array, alloc)      // 0.8.0 — stable
sort::insertionsort(array)         sort::countingsort(array)
sort::sort(array)                  // chooses a good default
sort::sorted(alloc, array)         // returns a new sorted slice
sort::binarysearch(sorted_array, key)?    // sz?  index when found
sort::is_sorted(array)
```

Comparator: `fn int cmp(T* a, T* b)` returning negative/zero/positive. Optional context with `cmp_with_ctx` variants.

---

## `std::encoding`

### `json`
```c3
Object*? json::parse(Allocator, String s, JsonFlavor flavor = JSONC)   // from string
Object*? json::tparse(String s, JsonFlavor flavor = JSONC)
Object*? json::load(Allocator, InStream s, JsonFlavor flavor = JSONC)  // from stream
Object*? json::temp_load(InStream s, JsonFlavor flavor = JSONC)
// JsonFlavor: JSON | JSONC   (JSONC allows comments + trailing commas — default)

// Object usage (std::collections::object — JSON DOM)
obj.get_string("key")?       obj.get_int("key")?     obj.get_object("key")?
obj.set("key", val)          obj.append(item)        obj.iter() // for objects/arrays
obj.kind                     // TYPE_NULL / TYPE_BOOL / TYPE_INT / TYPE_REAL / TYPE_STRING / TYPE_OBJECT / TYPE_ARRAY
obj.to_value(T)              // 0.8.0: structured conversion to a struct
```

### `ini`  (new in 0.8.0 encoder)
```c3
Object*? ini::parse(Allocator, String, char delim='=')
Object*? ini::tparse(String, char delim='=')
Object*? ini::load(Allocator, InStream, char delim='=')
String   ini::encode(Allocator, Object*, char delim='=', bool pad=true)
long?    ini::save(OutStream, Object*, char delim='=', bool pad=true)
// Faults: INVALID_SECTION, INVALID_KEY, DUPLICATE_KEY
// Constant: ini::GLOBAL = "" for top-level keys
```

### `csv`
```c3
CsvReader r;     r.init(stream, separator = ",");
CsvRow? row = r.read_row(alloc);    r.tread_row()    r.skip_row()
row.get_col(idx)    row.len()    row.free()
csv::@each_row(stream, separator = ","; |row| { ... })
```

### `base64`, `base32`, `hex`
```c3
// base64 (alphabets: STANDARD, URL)
String base64::encode(alloc, src, padding = '=', &STANDARD)
String base64::tencode(src, padding = '=', &STANDARD)
char[]? base64::decode(alloc, src, padding = '=', &STANDARD)
char[]? base64::tdecode(src)
String  base64::encode_into(dst_buf, src, padding = '=', &STANDARD)
char[]? base64::decode_into(dst_buf, src)
sz base64::encode_len(n, padding)     sz? base64::decode_len(n, padding)

// hex (same shape as base64; no alphabet/padding params)
hex::encode(alloc, src) / tencode(src) / encode_into(dst, src)
hex::decode(alloc, src) / tdecode(src) / decode_into(dst, src)
```

### `xml` (new in 0.8.0) — XML parsing + serialization.
### `pem` — PEM containers.
### `codepage` — Single-byte encoding tables.

---

## `std::hash`

Hashing structs are all `init / update(data) / final()`. Top-level `hash(data)` shortcut where useful.

| Module | Constants | Top-level | Struct | HMAC alias |
|--------|-----------|-----------|--------|------------|
| `sha256` | `HASH_SIZE=32` | `sha256::hash(data)` | `Sha256` | `HmacSha256`, `hmac`, `pbkdf2` |
| `sha512` | `HASH_SIZE=64` | `sha512::hash(data)` | `Sha512` | yes |
| `sha1`   | `HASH_SIZE=20` | `sha1::hash(data)`   | `Sha1`   | yes |
| `md5`    | `HASH_BYTES=16` | `md5::hash(data)`   | `Md5`    | yes |
| `crc32`  | -            | `crc32::hash(data)`  | `Crc32 (seed)` | - |
| `crc64`  | -            | `crc64::hash(data)`  | `Crc64`  | - |
| `blake2`, `blake3`, `whirlpool`, `ripemd`, `metro64`, `metro128`, `siphash`, `murmur`, `wyhash2`, `komi`, `a5hash`, `fnv32a`, `fnv64a`, `adler32`, `poly1305`, `gost` | … same shape … | | | |

```c3
char[32] digest = sha256::hash(data);

// Streaming usage
Sha256 ctx;     ctx.init();    ctx.update(chunk1);    ctx.update(chunk2);
char[32] out = ctx.final();

// HMAC
char[32] mac = sha256::hmac(key, data);
```

---

## `std::crypto`

```c3
// AES (modes: ECB, CBC, CTR)
Aes aes;   aes.init(AES128 | AES192 | AES256, key, iv, mode = CTR);
char[] ct = aes.encrypt(alloc, plain);   // or .tencrypt()
char[] pt = aes.decrypt(alloc, cipher);  // or .tdecrypt()
aes.encrypt_buffer(in, out);   aes.decrypt_buffer(in, out);
aes.destroy();

// ChaCha20
ChaCha20 c;   c.init(key[32], nonce[12], counter = 0);   c.transform(buf);
char[] ct = chacha20::encrypt(alloc, key, nonce, plain);  // alias `crypt_clone`
char[] pt = chacha20::decrypt(alloc, key, nonce, cipher);

// Argon2 password hashing
crypto::argon2::hash(...)

// Ed25519 signatures, Diffie-Hellman, RC4
ed25519::sign(...), ed25519::verify(...)        dh::generate_keypair(...)
crypto::entropy::random_bytes(buf)?             crypto::entropy::random_int()?
```

---

## `std::compression`

```c3
// DEFLATE (RFC 1951)
char[]? deflate::compress(alloc, input)             char[]? deflate::decompress(alloc, input)
void?   deflate::compress_stream(alloc, InStream in, OutStream out)
void?   deflate::decompress_stream(InStream in, OutStream out)

// gzip (RFC 1952) — wraps DEFLATE with header/CRC
char[]? gzip::compress(alloc, src, hcrc=false, char[] extra={}, String name="", String comment="")
Gzip?   gzip::uncompress(alloc, src)             // returns Gzip (with metadata)
char[]? gzip::uncompress_bytes(alloc, src)
void?   gzip::compress_stream(OutStream w, src, hcrc=false, …)
void?   gzip::uncompress_stream(OutStream w, InStream src)

// ZIP archives
ZipArchive? zip::open(alloc, path, mode = "r")          ZipArchive? zip::recover(alloc, path)
za.close()                  za.count()              za.stat(filename) / za.stat_at(idx)
za.read_file_all(alloc, name, password = "")
za.write_file(name, data, method = DEFLATE)             za.add_directory(name)
za.extract(output_dir, password = "")
za.open_reader(name, password = "")?  // ZipEntryReader (InStream)
za.open_writer(name, method = DEFLATE)?  // ZipEntryWriter (OutStream)

// QOI image format
char[]? qoi::encode(alloc, pixels, &desc)        char[]? qoi::decode(alloc, data, &desc, channels = AUTO)
sz?     qoi::write(filename, pixels, &desc)      char[]? qoi::read(alloc, filename, &desc, channels = AUTO)
```

---

## `libc` — C library bindings

`import libc;` exposes `libc::printf`, `libc::malloc`, `libc::free`, `libc::strlen`, `libc::memcpy`, `libc::stat`, etc. — typed wrappers around the platform C runtime.

```c3
import libc;
libc::printf("Hello %s\n", "world");
void* p = libc::malloc(1024);
libc::free(p);
```

---

## Format Specifier Reference (`io::printf` family)

| Spec | Meaning |
|------|---------|
| `%s` | String (works on String, ZString, DString, primitive-with-Printable, enums, vectors) |
| `%d` | Decimal integer (signed or unsigned, any width up to int128) |
| `%x` / `%X` | Hex (lower / upper) |
| `%o` | Octal |
| `%b` | Binary |
| `%f` | Floating point fixed |
| `%g` / `%e` | Float general / scientific |
| `%c` | Character |
| `%p` | Pointer |
| `%h` | Hash-like compact form |
| `%%` | Literal `%` |

Width / precision / flags work like C printf: `%-10.2f`, `%+05d`, `%.*s` etc.

---

## Cheat: Build-Time and Custom Stream Examples

```c3
// Implement an OutStream
struct CountingWriter (OutStream) { sz total; }
fn sz? CountingWriter.write(&self, char[] data) @dynamic { self.total += data.len; return data.len; }
fn void? CountingWriter.write_byte(&self, char c) @dynamic { self.total++; return; }

// Implement an InStream
struct StringReader (InStream) { String data; sz pos; }
fn sz?   StringReader.read(&self, char[] buf) @dynamic { ... }
fn char? StringReader.read_byte(&self) @dynamic { ... }
```
