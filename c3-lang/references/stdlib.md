# C3 Standard Library Reference (0.8.3)

Curated index of the most useful APIs in the C3 stdlib. For exhaustive lists, browse [github.com/c3lang/c3c/tree/v0.8.3/lib/std](https://github.com/c3lang/c3c/tree/v0.8.3/lib/std).

> **Code-block convention:** Most fenced blocks below are reference summaries — method signatures, free-function call shapes, and option lists packed onto few lines for scannability. They are **not compilable C3** and are tagged `text` rather than `c3` to disable syntax highlighting. Where a section shows real, runnable C3 (e.g. the `libc` import, the custom-stream example), it is tagged `c3`.

**Conventions used below:**
- `T?` is an Optional (may carry a fault). Always handle with `!`, `??`, `!!`, or `if (catch …)`.
- `t*` prefix = temporary-allocator variant (uses `tmem`, freed at `@pool()` exit).
- Method receivers: `(&self, …)` means pointer receiver (mutating).
- `Allocator` is the standard allocator interface — pass `mem` (heap) or `tmem` (temp).

---

## Module Index

Every public module shipped with the C3 0.8.3 standard library. Submodules are listed under their parent.

| Module | What it provides |
|---|---|
| **Built-ins** (`@builtin`, no import) | `mem::*` allocators, `@swap/@addr/@typeid/@ok/@catch/@try`, `@likely/@unlikely/@expect`, `@prefetch`, `bitcast/anycast/enum_by_name`, `@str_*` compile-time string ops, `v.hash()`, common faults |
| **`std::atomic`** | `Atomic{T}` wrapper, `atomic::fetch_{add,sub,or,and,xor,max,min}`, `flag_set/flag_clear`, ordering enum |
| **`std::bits`** | Integer/vector bit-twiddling macros: `reverse`, `bswap`, `popcount`, `ctz`, `clz`, `rotl`, `rotr`, `fshl`, `fshr` |
| **`std::collections`** | Container modules (see below) |
| ↳ `collections::anylist` | Heterogeneous list (typedef of `InterfaceList{any}`) — typed pop/get/first/last via `anycast` |
| ↳ `collections::bitset` | `BitSet{N}` — fixed-size bitset |
| ↳ `collections::growablebitset` | `GrowableBitSet{T}` — growable bitset |
| ↳ `collections::deque` | Double-ended growable queue |
| ↳ `collections::enummap` | `EnumMap{Enum, V}` — fixed array indexed by enum ordinal |
| ↳ `collections::enumset` | `EnumSet{Enum}` — bitset over enum ordinals |
| ↳ `collections::fixedlist` | `FixedList{T, N}` — stack-allocated, fixed capacity |
| ↳ `collections::map` | `HashMap{K, V}`, `OrderedMap{K, V}` — hash maps |
| ↳ `collections::set` | `HashSet{T}`, `OrderedSet{T}` — hash sets |
| ↳ `collections::interfacelist` | `InterfaceList{Iface}` — list of interface-typed values (base of `AnyList`) |
| ↳ `collections::blockingqueue` | Thread-safe linked blocking queue |
| ↳ `collections::linkedlist` | Doubly linked list |
| ↳ `collections::list` | `List{T}` — dynamic array |
| ↳ `collections::maybe` | `Maybe{T}` — explicit optional wrapper |
| ↳ `collections::object` | `Object` — JSON DOM (used by `json` / `ini` / `csv`) |
| ↳ `collections::priorityqueue` | `PriorityQueue{T}` / `PriorityQueueMax{T}` (binary heap) |
| ↳ `collections::range` | `Range{T}` / `ExclusiveRange{T}`; `range::upto/inclusive/exclusive` + `.to_array()` added 0.8.3 |
| ↳ `collections::result` | `Result{Ok, Err}` — error-with-payload; prefer built-in optionals in most cases |
| ↳ `collections::ringbuffer` | `RingBuffer{T, N}` — fixed-capacity circular buffer |
| ↳ `collections::sortedmap` | `SortedMap{K, V}` — skip-list ordered map |
| ↳ `collections::pair` | `Pair{A, B}` |
| ↳ `collections::triple` | `Triple{A, B, C}` |
| **`std::compression`** | deflate / gzip / zip / qoi |
| ↳ `compression::deflate` | RFC 1951 raw deflate, one-shot + streaming |
| ↳ `compression::gzip` | RFC 1952 gzip wrapper around deflate |
| ↳ `compression::qoi` | QOI image encode/decode, file I/O |
| ↳ `compression::zip` | ZIP archive read/write/extract |
| **`std::core`** | Core types & utilities (see below) |
| ↳ `core::alloc` | Low-level allocator primitives |
| ↳ `core::allocators` | Concrete allocator implementations (arena, page, …) |
| ↳ `core::ansi` | ANSI escape-sequence constants and helpers |
| ↳ `core::array` | `array::contains/index_of`, `array::contains_slice/index_of_slice`, `array::@filter/zip/reduce/any/all/…` |
| ↳ `core::ascii` | `is_*`/`to_*` char predicates, `AsciiCharset` bitmaps |
| ↳ `core::bitorder` | Endian / bit-order conversion |
| ↳ `core::builtin` | Built-in helpers (see `Built-ins` section above) |
| ↳ `core::builtin_comparison` | `equals`, `compare`, `less`, `greater` over arbitrary types |
| ↳ `core::cinterop` | Helpers for C interop (struct layout, calling-convention macros) |
| ↳ `core::conv` | Unicode BOM / UTF-8 ↔ UTF-16 ↔ UTF-32 conversion |
| ↳ `core::dstring` | `DString` — mutable dynamic string |
| ↳ `core::env` | Compile-time platform/compiler constants (`env::LINUX`, `env::WIN32`, …) |
| ↳ `core::logging` | Severity-tagged logging (`log`, `log_warning`, …) |
| ↳ `core::mem` | `mem::new/alloc/`, `mem::copy/move/clear/set/equals`, `@pool`, `Volatile`, `UnalignedRef` |
| ↳ `core::mem_mempool` | Fixed-size slab / mempool allocator |
| ↳ `core::refcount` | `RefCounted` helper for intrusive reference counting |
| ↳ `core::runtime` | Runtime startup / panic / fault helpers |
| ↳ `core::runtime_benchmark` | `@benchmark` infrastructure |
| ↳ `core::runtime_test` | `@test` infrastructure (`assert_eq`, `test_eq`, …) |
| ↳ `core::slice2d` | 2-D slice operations (`slice2d::get`, `set`, `row`, `col`, …) |
| ↳ `core::string` | `String` / `ZString` / `WString`, `string::format/tformat/bformat/join/split/…` |
| ↳ `core::string_escape` | `escape` / `unescape` for JSON / C / shell / URL-style strings |
| ↳ `core::string_iterator` | `StringIterator` over codepoints / graphemes |
| ↳ `core::string_to_real` | Internal float-parsing helpers |
| ↳ `core::test` | Test framework macros (`@test`, `test::fails`, `test::eq`, …) |
| ↳ `core::types` | Compile-time type predicates (`types::is_int`, `is_equatable`, `flat_kind`, …) |
| ↳ `core::values` | Misc value constants |
| **`std::crypto`** | Symmetric ciphers, KDF, signatures, RNG |
| ↳ `crypto::aes` | `Aes` — AES-128/192/256, ECB/CBC/CTR |
| ↳ `crypto::argon2` | Argon2id password hashing |
| ↳ `crypto::chacha20` | `ChaCha20` stream cipher + `crypt_clone` |
| ↳ `crypto::dh` | Diffie-Hellman keypair generation |
| ↳ `crypto::ed25519` | `ed25519::sign` / `ed25519::verify` |
| ↳ `crypto::entropy` | `entropy::fill(buffer)` / `entropy::make(alloc, length)` |
| ↳ `crypto::keccak` | Keccak / SHA-3 / Shake primitives |
| ↳ `crypto::rc4` | `Rc4` stream cipher (legacy) |
| **`std::encoding`** | Text & data encoding formats (see below) |
| ↳ `encoding::base32` | Base32 encode/decode |
| ↳ `encoding::base64` | Base64 encode/decode (STANDARD + URL alphabets) |
| ↳ `encoding::codepage` | Single-byte code-page tables |
| ↳ `encoding::csv` | `CsvReader`, `csv::@each_row` |
| ↳ `encoding::hex` | Hex encode/decode |
| ↳ `encoding::ini` | INI parse + encode |
| ↳ `encoding::json` | `json::parse/tparse/load`, `JsonFlavor` enum |
| ↳ `encoding::pem` | PEM block parse/encode |
| ↳ `encoding::xml` | XML parse + serialize |
| **`std::experimental`** | Unstable APIs — API/behavior may change between releases |
| ↳ `experimental::scheduler` | Frame-budgeted task scheduler (real-time / game-loop helper) |
| **`std::hash`** | Hashing primitives (see below) |
| ↳ `hash::sha1`, `hash::sha256`, `hash::sha512` | SHA family (struct + `sha*::hash()` shortcut) |
| ↳ `hash::md5` | MD5 |
| ↳ `hash::blake2`, `hash::blake3` | BLAKE2 / BLAKE3 |
| ↳ `hash::whirlpool` | Whirlpool |
| ↳ `hash::ripemd` | RIPEMD-160 |
| ↳ `hash::crc32`, `hash::crc64` | CRC |
| ↳ `hash::adler32` | Adler-32 |
| ↳ `hash::fnv32a`, `hash::fnv64a` | FNV-1a |
| ↳ `hash::murmur3` | MurmurHash3 |
| ↳ `hash::wyhash2` | wyhash |
| ↳ `hash::siphash` | SipHash |
| ↳ `hash::metro64`, `hash::metro128` | MetroHash |
| ↳ `hash::komi` | KomiHash |
| ↳ `hash::a5hash` | A5Hash |
| ↳ `hash::poly1305` | Poly1305 MAC |
| ↳ `hash::streebog` | GOST R 34.11-2012 (Streebog) |
| ↳ `hash::hmac` | Generic `hmac` (works with any digest above) |
| **`std::io`** | I/O, files, paths, streams (see below) |
| ↳ `io::` | `io::print/printn/printf`, `io::readline`, `InStream` / `OutStream` interfaces, stream helper types |
| ↳ `io::file` | `File` type, `file::open/load/save/exists/…` |
| ↳ `io::file::mmap` | Memory-mapped `File` |
| ↳ `io::path` | `Path` (`PathPosix` / `PathWin`), `path::cwd/home/temp/ls/…` |
| **`libc`** | Typed wrappers around the platform C runtime (`libc::printf`, `libc::malloc`, `libc::errno()`, …). Top-level module — not `std::libc` |
| **`std::math`** | Math functions, vectors, matrices (see below) |
| ↳ `math::` | Trig/exp/log, `abs/sign/clamp/min/max`, `PI/E`, float-type limits |
| ↳ `math::bigint` | Arbitrary-precision integers |
| ↳ `math::complex` | `Complex{R/I}` |
| ↳ `math::matrix` | `Matrix2/3/4`, `Matrix2f/3f/4f`, etc. |
| ↳ `math::quaternion` | `Quaternionf` |
| ↳ `math::vector` | Vector (`T[<N>]`) helpers — `length`, `normalize`, `dot`, `cross`, `lerp`, `transform`, … |
| ↳ `math::random` | `DefaultRandom`, `Sfc64Random`, `Pcg32Random`, `Mt19937Random`, `ChaCha20Random`, `math::srand/rand/rnd` |
| ↳ `math::distributions` | Statistical distributions (`normal`, `uniform`, `bernoulli`, …) |
| ↳ `math::easing` | Easing functions (`ease_in_sine`, `ease_out_cubic`, …) |
| ↳ `math::rectangle` | `Rectangle{T}` — Ray/AABB/Sphere intersection helpers; `Bounds` / `BoundingBox{T}` (min/max region, inclusive edges) added 0.8.3. `Rect.contains_point` is exclusive on the max edge as of 0.8.3. |
| ↳ `math::uuid` | UUID v1/v3/v4/v5 generation |
| **`std::net`** | Networking (see below) |
| ↳ `net::inetaddr` | `InetAddress` (IPv4/IPv6), part of `std::net` |
| ↳ `net::` | Socket base types, socket options, poll, connect helpers |
| ↳ `net::tcp` | `TcpSocket`, `TcpServerSocket`, `tcp::connect/listen/accept` |
| ↳ `net::udp` | `UdpSocket`, `udp::connect` |
| ↳ `net::url` | `url::parse`, `Url`, `UrlQueryValues`, `url_encode` / `url_decode` |
| **`std::os`** | Process control, env, backtrace, CPU detection (see below) |
| ↳ `os::process` | `Process`, `os::process::spawn/run`, `p.join/terminate/stdout/stderr/…` |
| ↳ `os::env` | `os::env::get_var/set_var`, `get_home_dir`, `get_config_dir`, `executable_path` |
| ↳ `os::backtrace` | `os::backtrace::capture_current/get` |
| ↳ `os::` | `os::num_cpu()` — logical core count (declared directly in `std::os`, per-platform) |
| **`std::sort`** | `quicksort`, `mergesort`, `insertionsort`, `countingsort`, `binarysearch`, `is_sorted`, `sorted` |
| **`std::thread`** | Threading primitives (see below) |
| ↳ `thread::` | `Thread`, `thread::sleep/yield`, mutex + condvar + once |
| ↳ `thread::pool` | `ThreadPool` (deprecated 0.8.1) |
| ↳ `thread::threadpool` | `FixedThreadPool` (deprecated 0.8.1) |
| ↳ `thread::channel` | `BufferedChannel{T}`, `UnbufferedChannel{T}`, `UnboundedChannel{T}`, `OneShotChannel{T}` |
| ↳ `thread::cpu` | `native_cpu()` — logical core count |
| ↳ `thread::experimental::threadgroup` | `ThreadGroup{Task, Result}` — worker-pool abstraction (preferred over `ThreadPool`/`FixedThreadPool`) |
| **`std::time`** | `Time`, `Duration`, `NanoDuration`, `DateTime` / `TzDateTime`, `Clock` |

---

## `std::bits` — Bit manipulation

All available as macros (or methods on the matching integer/vector type). The macros also work on integer vectors (`int[<3>]`, etc.):

```text
// Compile-time (no `self` argument)
bits::reverse(x)   // bit-reversal
bits::bswap(x)     // byte-swap

// Per-type methods — same name on every int width (ichar/char/short/ushort/int/uint/
//                   long/ulong/int128/uint128 + the same widths as vectors)
v.popcount()    v.ctz()       v.clz()        // count bits set / trailing / leading zeros
v.fshl(hi, lo, n)             v.fshr(hi, lo, n)   // funnel shift
v.rotl(n)     v.rotr(n)                       // bit rotation

// All except fshl/fshr return `int` (popcount) or the same type (rotl/rotr, fshl/fshr).
```

---

## Built-ins (`@builtin`, no import needed)

Always in scope, even without `import std::core::…`:

```text
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

```text
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
// interface methods take no receiver; implementations add `self` + @dynamic
interface InStream  { fn char? read_byte();  fn sz? read(char[] buf); … }
interface OutStream { fn void? write_byte(char c);  fn sz? write(char[] data); … }

// Format string: %s, %d, %x, %X, %o, %b, %f, %g, %e, %c, %p, %h
// No width-type qualifiers (no %lld/%u/%zu) — %d handles all integer widths.
```

### Reading from an `InStream`

Four helpers, differing only in how they treat a short read / EOF. Picking the wrong one is a common source of silent truncation bugs.

```text
sz?     io::read_buffer(stream, char[] buf)          // one read; EOF -> 0, not a fault. buf must be non-empty
char[]? io::read_buffer_to_end(stream, char[] buf)   // loops until buf is full or EOF; returns the prefix actually read
sz?     io::read_all(stream, char[] buf)             // like the above, but a short read is io::UNEXPECTED_EOF
char[]? io::read_fully(alloc, stream)                // reads to end of stream, allocating
```

```c3
// 5-byte stream, 10-byte buffer:
io::read_buffer(&r, buf[:10])           // => 5   (then 0 on the next call, at EOF)
io::read_buffer_to_end(&r, buf[:10])    // => slice of len 5
io::read_all(&r, buf[:10])              // => fault io::UNEXPECTED_EOF
```

A single `read_buffer` may return fewer bytes than requested even mid-stream, so loop on it (or use `read_buffer_to_end`) rather than assuming one call fills the buffer. `read_buffer` returning `0` is the EOF signal — it swallows the `io::EOF` the underlying `stream.read` raises. Call the raw `stream.read(buf)` interface method directly only if you want that `io::EOF` fault instead.

### Implementing `InStream` / `OutStream` on your own types

Use `@dynamic` so the methods are looked up at runtime via the interface:

```c3
// OutStream — counts bytes written
struct CountingWriter (OutStream) { sz total; }
fn sz? CountingWriter.write(&self, char[] data) @dynamic { self.total += data.len; return data.len; }
fn void? CountingWriter.write_byte(&self, char c) @dynamic { self.total++; return; }

// InStream — reads from an in-memory String
struct StringReader (InStream) { String data; sz pos; }
fn sz?   StringReader.read(&self, char[] buf) @dynamic { … }
fn char? StringReader.read_byte(&self) @dynamic { … }
```

### `printf` format specifiers

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

### `std::io::file`

```text
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

`Path` is `PathPosix` or `PathWin` depending on the platform. It implicitly casts to `String`.

```text
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

### `std::io::file::mmap` — memory-mapped files
```text
FileMmap? file::mmap_file(File file, sz offset = 0, sz len = 0, VirtualMemoryAccess access = READ, bool shared = false)
FileMmap? file::mmap_open(String filename, String mode, sz offset = 0, sz len = 0, VirtualMemoryAccess access = READ, bool shared = false)
char[]    m.bytes()                                    // raw byte view
void?     m.destroy()
```

---

## `std::collections` — Containers

All containers come in two init flavors: `.init(alloc, ...)` heap, `.tinit(...)` temp. All take a `Type` (or `Key`/`Value`) generic parameter — instantiate with `alias MyList = List{int};`.

### `List{T}` — dynamic array
```text
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

### `FixedList{T, SIZE}` — stack-allocated fixed-cap list. Same API as `List` plus `push_try()`, `push_all_to_limit()`, `is_full()` (0.8.3).

### `HashMap{K, V}` — open-addressed hash map
```text
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
```text
HashSet{int} s;   s.init(mem);
s.add(v)    s.add_all(arr)    s.contains(v)    s.remove(v)    s.len()
s.set_union(alloc, &other)         s.intersection(alloc, &other)
s.difference(alloc, &other)        s.symmetric_difference(alloc, &other)
s.is_subset(&other)                s.iter()
```

### `SortedMap{K, V}` — skip-list ordered map
```text
SortedMap{int, String} m;   m.init(mem);
m.set(k, v)   m.get(k)   m.remove(k)   m.has_key(k)
m.first_key() / m.last_key()      m.pop_first() / m.pop_last()
m.floor_key(k)   m.ceiling_key(k)   m.lower_key(k)   m.higher_key(k)
m.iter()   m.iter_from(k)   m.iter_range(from, to)
m.clone(alloc)   m.merge(&other)
```

### `Deque{T}`, `LinkedList{T}`, `RingBuffer{T, N}`
```text
// Deque (double-ended growable)
d.push(v)  d.push_front(v)  d.pop()  d.pop_first()  d.first() / d.last()
d.get(i)   d.set(i, v)      d.reserve(extra)  d.shrink()  d.normalize()
d.pop_into(slice)  d.pop_first_into(slice)   d.prepend(slice)   // prepend: 0.8.3
// LinkedList also gained prepend(slice) in 0.8.3
// RingBuffer — fixed-cap circular; push, pop_first, first, last, get, set
```

### `Range{T}` / `ExclusiveRange{T}`
```c3
// constructor macros (0.8.3) — infer T from the arguments
foreach (i : range::upto(3))          { }   // 0,1,2,3  — inclusive of `to`
foreach (i : range::inclusive(1, 3))  { }   // 1,2,3
foreach (i : range::exclusive(1, 3))  { }   // 1,2
int[] a = range::inclusive(1, 3).to_array(mem);   // .to_array: 0.8.3
r.len()   r.contains(v)   r[i]
```

### `PriorityQueue{T}` / `PriorityQueueMax{T}`
```text
PriorityQueue{int} q;   q.init(mem);
q.push(v)   q.pop()    q.first()    q.remove_at(idx)   q.len()
```

### `BitSet{SIZE}` / `GrowableBitSet{T}`
```text
BitSet{1024} b;
b.set(i)   b.unset(i)   b.get(i)   b.set_bool(i, v)   b.cardinality()
b.or(other) / b.and(other) / b.xor(other)    // operators: | & ^ |= &= ^=
```

### `EnumMap{Enum, V}` — fixed-size map keyed by an enum
```text
EnumMap{Color, String} m;   m.init("");  // default for unset keys
m.set(RED, "warm");        m.get(BLUE)?  // String?
m.get_ref(RED);                       // for in-place mutation
m.len()   // == Enum::len
```

### `EnumSet{Enum}` — bitset over an enum's values
```text
EnumSet{Color} s;   s.init();
s.add(RED)  s.add(BLUE)  s.remove(GREEN)  s.contains(RED)
s.set_union(&other)   s.intersection(&other)   s.difference(&other)
s.values();   // iterate
```

### `Result{Ok, Err}` — value-or-error-with-payload
```text
// Use only when the error path carries structured data; otherwise prefer
// C3's built-in optionals (T? / fault).
Result{int, String} r = ok(42);
Result{int, String} b = err("oops");
r.ok()?          // 42 or RESULT_ERROR~
r.err()?         // String or RESULT_OK~
r.@or_else(; e) { return e; }   // diverges on error — requires @body to return/break/etc
```

### `Maybe{T}` — explicit optional wrapper
```text
Maybe{int} m;        // equivalent to int? — present or empty
if (try v = m) { ... }
```

### `AnyList` / `InterfaceList{Iface}` — heterogeneous lists
```text
// AnyList = typedef InterfaceList{any}  — store mixed types, retrieve typed
AnyList list;   list.init(mem);
list.push(42);  list.push("hello");
list.push(Point{ 1, 2 });

int n = list.first(int);          // typed pop
String s = list.get(1, String);   // typed get by index
any v = list.first_any();         // untyped (caller's responsibility)
list.len();
```

### Other collection types: `Tuple` family, `Range{T}`, `ExclusiveRange{T}`, `OrderedMap{K, V}`, `OrderedSet{T}`, `LinkedBlockingQueue{T}`, `InterfaceList{Iface}` (base of `AnyList`).

`OrderedMap` / `OrderedSet` were named `LinkedHashMap` / `LinkedHashSet` before 0.8.1; the old names still resolve but are deprecated.

---

## `std::core::string`

```text
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
s.strip_prefix(prefix)     s.strip_suffix(suffix)   // formerly strip / strip_end
s.starts_with(p)           s.ends_with(p)
s.contains(sub)            s.contains_char(c)
s.index_of(sub)            s.rindex_of(sub)     // 0.8.2: empty `sub` is accepted
s.index_of_char(c)         s.index_of_char_from(c, start)   s.rindex_of_char(c)
s.index_of_chars(char_slice)
s.count(sub)               s.compare_to(other)       s.compare_to_ignore_case(other)
s.to_lower(alloc) / s.tlower()    s.to_upper(alloc) / s.tupper()
s.zstr_copy(alloc)         s.zstr_tcopy()
s.hash()                   s.free(alloc)

// ZString methods
zs.str_view()              zs.char_len()        zs.len()        zs == other (.eq)

// Parsing into integers / floats (find on `int.parse`, `long.parse`, `float.parse`, etc.)
int? int::parse(s, int radix = 10)        // stdlib offers parse() helpers per type
```

### `std::core::dstring` — DString (dynamic, mutable string)

```text
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

```text
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

```text
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
env::AUTHORS   env::AUTHOR_EMAILS   env::PROJECT_VERSION   env::PROJECT_PATH
```

Use in `$if env::ARCH_64_BIT:` etc. For conditional top-level declarations use `@feat(WIN32)` (0.8.3; `@if` there is deprecated) — `@feat` takes a bare flag, `$if` takes an `env::` constant.

---

## `std::core::array`

Functional helpers — most are macros, work on any array-like:

```text
array::contains(arr, v)           array::index_of(arr, v)         array::rindex_of(arr, v)
array::contains_slice(arr, needle)   array::index_of_slice(arr, needle)   // subsequence search, sz?
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

```text
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

```text
// Constants
math::PI        math::HALF_PI       math::QUARTER_PI      math::INV_PI
math::TAU       math::TWO_PI        // TWO_PI is an alias for TAU
math::TWO_OVER_PI    math::TWO_OVER_SQRT_PI
math::E         math::LOG2E         math::LOG10E
math::LN2       math::LN10          math::SQRT2          math::INV_SQRT2
math::FLOAT_MAX / FLOAT_MIN / FLOAT_DENORM_MIN / FLOAT_EPSILON
math::HALF_MAX / HALF_MIN / HALF_EPSILON …  (same for double/float128/bfloat16)

// Trig / exponential / power (operate on float, double, float128, vectors)
math::sin(x)   math::cos(x)   math::tan(x)   math::asin(x)   math::acos(x)   math::atan(x)
math::atan2(y, x)
math::sinh(x)  math::cosh(x)  math::tanh(x)  math::asinh(x)  math::acosh(x)  math::atanh(x)
math::csc(x)   math::sec(x)   math::cot(x)    // formerly cosec, cotan
math::exp(x)   math::exp2(x)  math::exp10(x)
math::log(x, base)             math::log2(x)   math::log10(x)   math::ln(x)
math::pow(x, y)   math::sqrt(x)   math::cbrt(x)   math::hypot(a, b)

// Numeric
math::abs(x)   math::sign(x)   math::clamp(x, lo, hi)
math::min(a, b, …)   math::max(a, b, …)
math::ceil(x)  math::floor(x)  math::round(x)   math::trunc(x)
math::fmod(x, y)  math::mad(a, b, c)            // mad was formerly muladd
math::lerp(a, b, t)   math::lerp_smooth(a, b, t)
math::deg_to_rad(x)   math::rad_to_deg(x)
```

### `std::math::random`

```text
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

```text
// Predefined aliases (the underlying C3 vector type is T[<N>])
alias Vec2 @weak = float[<2>];   Vec3 = float[<3>];   Vec4 = float[<4>];
// int[<N>], double[<N>], long[<N>] vectors are also first-class.

// Any-width methods on float[<*>] / double[<*>]  (mirrored for both element types)
v.length()    v.length_sq()    v.normalize()    v.distance(o)   v.distance_sq(o)
v.dot(o)      v.sum()          v.product()      v.min() / v.max()
v.lerp(o, t)  v.reflect(o)     v.clamp(lo, hi)  v.clamp_length(min, max)
v.move_towards(target, max_dist)   v.equals(o) / v.not_equals(o)   v.is_normalized()
v.ceil() v.floor() v.round() v.trunc() v.rint() v.nearbyint() v.roundeven()
v.pow(exp)    v.fma(b, c)      v.copysign(sgn)
v.comp_lt(o) / comp_le / comp_eq / comp_gt / comp_ge / comp_ne   // -> bool[<*>] masks

// 2-element only
v.cross(v2) -> scalar    v.rotate(angle)    v.angle(v2)    v.transform(Matrix4f)
// 3-element only
v.cross(v2) -> vector    v.angle(v2)        v.perpendicular()   v.rejection(v2)
v.barycentric(a, b, c)   v.transform(mat)   v.refract(n, r)
v.rotate_quat(q)         v.rotate_axis(axis, angle)
v.project(model, proj, viewport)    v.unproject(model, proj, viewport)

// Free functions in the module
double[<3>] vector::cubic_hermite(v1, tangent1, v2, tangent2, double amount)   // + cubic_hermitef
void        vector::orthonormalize(double[<3>]* v1, double[<3>]* v2)           // + orthonormalizef
bool[<*>]   vector::mask_from_int($Type, mask)     mask.mask_to_int()
```

### Other math: `bigint`, `complex`, `matrix` (`Matrix2/3/4`, `Matrix2f/3f/4f`), `quaternion` (`Quaternionf`), `distributions`, `easing`, `shapes`, `uuid`.

---

## `std::time`

```text
// Duration / time constants (all in microseconds)
time::US time::MS time::SEC time::MIN time::HOUR time::DAY time::WEEK time::MONTH time::YEAR
time::DURATION_ZERO   time::FAR_FUTURE   time::FAR_PAST

// Helpers to build a Duration
time::us(n)  time::ms(n)  time::sec(n)  time::min(n)  time::hour(n)

// Time / Duration / NanoDuration
Time t = time::now();         // wall clock (microseconds since epoch)
Duration d = t1 - t0;         // arithmetic on Time values returns Duration
t.add_seconds(n)  t.diff_hours(other)  t.compare_to(other)  …
Duration.to_ms(d)  Duration.to_nano(d)
NanoDuration.to_ms(nd)  NanoDuration.to_sec(nd)  NanoDuration.to_duration(nd)

// DateTime — struct with fields .usec/.sec/.min/.hour/.day/.month/.weekday/.year/.year_day/.time
DateTime dt = datetime::now();
DateTime at = datetime::at(year, month=JANUARY, day=1, hour=0, min=0, sec=0, us=0);
TzDateTime tz = datetime::at_tz(year, ..., gmt_offset = 0);   // TzDateTime { inline DateTime date_time; int gmt_offset; }
DateTime from = datetime::from_time(Time t);
TzDateTime from_tz = datetime::from_time_tz(Time t, int gmt_offset);

dt.set(year, month, day, hour, min, sec, us)     dt.set_time(Time t)
dt.add_seconds/minutes/hours/days/weeks/months/years(n)   // return a new DateTime
dt.to_local()   dt.to_gmt_offset(offset)   dt.with_gmt_offset(offset)   // -> TzDateTime
// TzDateTime mirrors the add_*/to_gmt_offset/with_gmt_offset set, preserving its offset

// Format — free function taking the format first; also methods on both types
String datetime::format(Allocator, DateTimeFormat fmt, TzDateTime dt)
String datetime::tformat(DateTimeFormat fmt, TzDateTime dt)
String dt.format(Allocator, DateTimeFormat fmt)     // on DateTime (assumes UTC) and TzDateTime
// DateTimeFormat enum: ANSIC, UNIXDATE, RUBYDATE, RFC822, RFC822Z, RFC850, RFC1123, RFC1123Z, RFC3339, RFC3339Z, RFC3339MS, RFC3339ZMS, …

// Monotonic clock (for timing)
Clock c = clock::now();
NanoDuration elapsed = c.mark();      // restart + return time since last mark
NanoDuration since  = c.to_now();     // peek without restart
NanoDuration diff   = c1 - c2;        // Clock arithmetic via operator overloads
```

---

## `std::os`

```text
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

```text
String? os::env::get_var(Allocator, name)        String? os::env::tget_var(name)
bool    os::env::set_var(name, value, overwrite = true)
bool    os::env::clear_var(name)
String? os::env::get_home_dir(Allocator)
Path?   os::env::get_config_dir(Allocator)
String? os::env::executable_path()
```

### `std::os::backtrace` — `os::backtrace::capture_current(buf)`, `os::backtrace::get(Allocator)`.

### CPU detection
```text
int os::num_cpu()          // logical cores, directly under std::os
int thread::cpu::native_cpu()   // alternative, under std::thread::cpu
```

### XDG directories (POSIX)
There is no `std::os::xdg` module — `os/xdg.c3` declares `module std::os::posix` and exposes a single lookup:
```text
String? os::posix::xdg_user_dir_lookup(Allocator, String type)   // e.g. "DESKTOP", "DOWNLOAD"
```
For config/home/cache paths use `os::env::get_home_dir` / `get_config_dir` above.

---

## `std::net` — Networking

```text
// TCP
TcpSocket?       net::tcp::connect(String host, int port, Duration timeout = 0, SocketOption…)
TcpSocket?       net::tcp::connect_async(String host, int port, SocketOption…)
TcpServerSocket? net::tcp::listen(String host, int port, int backlog, SocketOption…)
TcpSocket?       net::tcp::accept(TcpServerSocket* server)
TcpSocketPair?   tcp::TcpSocketPair.init(&self)             // socket pair

// UDP
UdpSocket? net::udp::connect(String host, int port, SocketOption…)
UdpSocket? net::udp::connect_async(String host, int port, SocketOption…)

// Socket (TcpSocket / UdpSocket implement InStream + OutStream); base type is std::net::Socket
s.read(buf)        s.write(buf)
s.close()          s.set_option(opt, val)   s.get_*  (broadcast, keepalive, reuseaddr, dontroute, oobline)
s.shutdown(SocketShutdownHow.RECEIVE/SEND/BOTH)

// Poll
Poll[] polls = { { .socket = fd, .events = READ | WRITE } };
ulong? net::poll(Poll[] polls, Duration timeout)
ulong? net::poll_ms(Poll[] polls, long timeout_ms)
net::POLL_FOREVER

// InetAddress
InetAddress? net::ipv4_from_str(s)        InetAddress? net::ipv6_from_str(s)
addr.is_loopback() / .is_multicast() / .is_link_local() / .is_site_local() / .is_any_local()
addr.to_string(alloc) / addr.to_tstring()
// IpProtocol enum: UNSPECIFIED, IPV4, IPV6

// URL — module std::net::url (not a separate "url_encoding" module)
Url? net::url::parse(Allocator, s)          Url? net::url::tparse(s)
UrlQueryValues net::url::parse_query(Allocator, query_string)
String url.to_string(alloc)
qv.add(key, value)         qv.free()
String  net::url::encode(Allocator, String s, UrlEncodingMode mode)   // %20 for space
String  net::url::tencode(String s, UrlEncodingMode mode)
String? net::url::decode(Allocator, String s, UrlEncodingMode mode)   // %20 → space; fault on invalid
String? net::url::tdecode(String s, UrlEncodingMode mode)
// UrlEncodingMode enum: UNRESERVED, PATH, HOST, USERPASS, QUERY, FRAGMENT
```

Low-level socket plumbing (`NativeSocket`, `socket()`, `bind()`, `connect()`, `accept()`, `getsockopt`/`setsockopt`, `socketpair`) lives in `std::net::os` — most users never touch it directly; it's the base of `net::tcp` / `net::udp`.

---

## `std::thread`

```text
// Threads
Thread t;     t.create(&worker_fn, arg, ThreadSettings{...})?    t.join()?    t.detach()?
thread::current()           // -> Thread, the calling thread
t.set_priority(ThreadPriority prio)   // instance method, not a free function
thread::sleep(Duration d)   thread::sleep_ms(long ms)   thread::sleep_ns(NanoDuration ns)
thread::yield()
// Stack size / priority are set at creation time via ThreadSettings{ .stack_size = …, .priority = … }
// passed to t.create(...) — there is no separate thread::set_stack_size function.

// Mutexes (initialize before use)
Mutex m;   m.init()?     m.lock()?    m.unlock()    m.try_lock()    m.destroy()
RecursiveMutex rm;          rm.init()?
TimedMutex tm;              tm.init()?    tm.lock_timeout(long ms)?
TimedRecursiveMutex trm;    trm.init()?

// Condition variables
ConditionVariable cv;       cv.init()?    cv.wait(&m)?    cv.signal()?    cv.broadcast()?
cv.wait_timeout(&m, ms_or_duration)?    cv.wait_until(&m, Time)?

// Once-init
OnceFlag o;        o.call(&init_fn)

// Channels — module std::thread::channel <Type>; all created via allocator, pointer-typed
BufferedChannel{int}*   bc = channel::create_buffered{int}(mem, size = 1)?;
UnbufferedChannel{int}* uc = channel::create_unbuffered{int}(mem)?;
UnboundedChannel{int}*  ec = channel::create_unbounded{int}(mem, start_size = 16)?;
OneShotChannel{int}*    oc = channel::create_one_shot{int}(mem)?;

// Blocking ops — push / pop (NOT send / recv)
bc.push(v)?    bc.pop()?    bc.close()    bc.destroy()

// Non-blocking variants
bc.try_push(v)?    bc.try_pop()?          // buffered + unbuffered
ec.try_pop()?                             // unbounded: try_pop only (push never blocks)
ec.clear()

// OneShotChannel: push / pop / close / destroy only — no try_* variants
```

**`ThreadPool(<SIZE>)` and `FixedThreadPool` are deprecated as of 0.8.1.** They still work, but new code should not build on them — prefer `std::thread::experimental::threadgroup`'s `ThreadGroup` for a worker pool.

### `std::thread::pool` — fixed-capacity generic thread pool (deprecated)
```text
ThreadPool(<8>) tp;         tp.init(ThreadSettings settings = {})?
tp.push(ThreadFn func, void* arg)      tp.join()    tp.destroy()    tp.stop_and_destroy()
```

### `std::thread::threadpool` — `FixedThreadPool` worker pool (deprecated)
```text
FixedThreadPool fp;    fp.init(sz threads, sz queue_size = 0, ThreadSettings settings = {})?
fp.push(ThreadPoolFn func, any[][] args...)?      fp.join()    fp.destroy()?    fp.stop_and_destroy()
```

---

## `std::atomic` — `Atomic{T}`

```text
Atomic{int} a;
a.load(SEQ_CONSISTENT)       a.store(5, SEQ_CONSISTENT)
a.add(1)   a.sub(1)   a.mul(2)   a.div(2)   a.max(5)   a.min(5)
a.or(0xFF)   a.and(mask)   a.xor(mask)   a.shr(2)   a.shl(2)
Atomic{bool} b;       b.set()    b.clear()        // test-and-set / clear

// Compare-and-swap: returns true on success; on failure `expected` is updated in place
bool ok = a.compare_exchange(&expected, desired);
bool ok = a.compare_exchange(&expected, desired, SEQ_CONSISTENT, SEQ_CONSISTENT);

// Plain-pointer atomics
atomic::fetch_add(&x, 1)     atomic::fetch_sub(&x, 1)     atomic::fetch_or(&x, m)
atomic::fetch_and(&x, m)     atomic::fetch_xor(&x, m)
atomic::flag_set(&b)         atomic::flag_clear(&b)
atomic::fetch_max(&x, v)     atomic::fetch_min(&x, v)
// Orderings: RELAXED, CONSUME, ACQUIRE, RELEASE, ACQUIRE_RELEASE, SEQ_CONSISTENT
```

---

## `std::sort`

```text
sort::quicksort(array)             sort::quicksort(array, cmp_fn)
sort::mergesort(array, alloc)      // stable
sort::insertionsort(array)         sort::countingsort(array)
sort::sort(array)                  // chooses a good default
sort::sorted(alloc, array)         // returns a new sorted slice
sort::binarysearch(sorted_array, key)?    // sz?  index when found
sort::is_sorted(array)
```

Comparator: `fn int cmp(T* a, T* b)` returning negative/zero/positive. Optional context with `cmp_with_ctx` variants.

---

## `std::encoding`

```text
// json  (JsonFlavor: JSON | JSONC — JSONC allows comments + trailing commas, default)
Object*? json::parse(alloc, String, JsonFlavor = JSONC)         // from string
Object*? json::tparse(String, JsonFlavor = JSONC)
Object*? json::load(alloc, InStream, JsonFlavor = JSONC)        // from stream
Object*? json::tload(InStream, JsonFlavor = JSONC)              // `temp_load` is a deprecated alias for this
// marshal / unmarshal directly between structs and JSON text (std::encoding::json)
String   json::marshal(alloc, value, JsonIndent = NONE)         // JsonIndent: NONE/TAB/SPACE_1..SPACE_5
String?  json::marshal_try(alloc, value, JsonIndent = NONE)     // fallible variant
void?    json::marshal_to(OutStream, value, JsonIndent = NONE)
json::unmarshal(alloc, input, $Type)                            // input: String or InStream
// same for an already-parsed DOM (std::collections::object)
Type?    object::unmarshal{Type}(alloc, Object*)                // frees slices on malformed data
void?    object::unmarshal_to(alloc, Object*, out_ref)          // out_ref must be a pointer
// Object usage (std::collections::object — JSON DOM)
obj.get_string("key")?       obj.get_int("key")?     obj.get("key")?          // .get() returns Object*?
obj.set("key", val)          obj.push(item)          obj.get_or_create_obj("key")
obj.type                     // typeid — compare against `bool`/`int128`/`double`/`String`/etc, not an enum
obj.to_value($Type)          // structured conversion to a struct/primitive

// ini   (parse + encode)
Object*? ini::parse(alloc, String, delim = '=')     Object*? ini::tparse(String, delim = '=')
Object*? ini::load(alloc, InStream, delim = '=')
String   ini::encode(alloc, Object*, delim = '=', pad = true)
long?    ini::save(OutStream, Object*, delim = '=', pad = true)
// Faults: INVALID_SECTION, INVALID_KEY, DUPLICATE_KEY. Constant: ini::GLOBAL = "" for top-level keys.

// csv
CsvReader r;     r.init(stream, separator = ",");
CsvRow? row = r.read_row(alloc);    r.tread_row()    r.skip_row()
row.get_col(idx)    row.len()    row.free()
csv::@each_row(stream, separator = ","; |row| { ... })

// base64 (alphabets: STANDARD, URL) / base32 / hex — same shape
String   base64::encode(alloc, src, padding = '=', &STANDARD)     String base64::tencode(src, …)
char[]?  base64::decode(alloc, src, padding = '=', &STANDARD)     char[]? base64::tdecode(src)
String   base64::encode_into(dst_buf, src, …)                      char[]? base64::decode_into(dst_buf, src)
sz       base64::encode_len(n, padding)                           sz? base64::decode_len(n, padding)
// hex: same shape minus alphabet/padding params; base32: same shape.

// xml   — parse + serialize.   See encoding::xml.
// pem   — PEM block parse/encode.             See encoding::pem.
// codepage — single-byte encoding tables.     See encoding::codepage.
```

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

```text
char[32] digest = sha256::hash(data);

// Streaming usage
Sha256 ctx;     ctx.init();    ctx.update(chunk1);    ctx.update(chunk2);
char[32] out = ctx.final();

// HMAC
char[32] mac = sha256::hmac(key, data);
```

---

## `std::crypto`

### High-traffic ciphers

```text
// AES (modes: ECB, CBC, CTR)
Aes aes;   aes.init(AesType type, key, iv, mode = CTR);   // type is ONE of AES128 / AES192 / AES256, not OR'd
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
```

### Other ciphers & primitives

```text
// Ed25519 signatures
ed25519::sign(...)         ed25519::verify(...)
// Diffie-Hellman
BigInt secret = dh::generate_secret(BigInt p, BigInt x, BigInt y)
BigInt pubkey = dh::public_key(BigInt p, BigInt g, BigInt x)

// RC4 (legacy stream cipher)
Rc4 c;    c.init(key);    c.crypt(src, dst, len);   // in-place if src == dst
// or: rc4::encrypt(alloc, key, plain) / decrypt(alloc, key, cipher)

// Keccak / SHA-3 / Shake — same init/update/final pattern as the hash structs
keccak::hash(data)?                           // one-shot, default Keccak-256
Sha3_256 ctx;   ctx.init();   ctx.update(chunk);   char[32] d = ctx.final();

// System entropy
void?   crypto::entropy::fill(char[] buffer, bool timeout = false)                 // fills buffer in place
char[]? crypto::entropy::make(Allocator allocator, sz length, bool timeout = false) // allocates a new buffer
```

---

## `std::experimental` — Unstable APIs

APIs here are shipped to gather feedback but **may change or be removed** between releases. Don't depend on them in production code without pinning a compiler version.

### `std::experimental::FrameScheduler`
```text
// Real-time / game-loop helper — schedule work within a per-frame budget.
FrameScheduler sched;
sched.init(.target_fps = 60, .budget_us = 16_000);
sched.run(|frame| {
    frame.time_ns;        // ns since last frame
    frame.remaining_us;   // budget left this frame
    // … update/render …
});
```

---

## `std::compression`

```text
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

`import libc;` exposes `libc::printf`, `libc::malloc`, `libc::free`, `libc::strlen`, `libc::memcpy`, `libc::stat`, etc. — typed wrappers around the platform C runtime. Use when you need a libc symbol that isn't in the rest of the stdlib (e.g. `libc::stat`, `libc::dlopen`, `libc::pthread_*` on POSIX).
