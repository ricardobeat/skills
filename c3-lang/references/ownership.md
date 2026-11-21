# C3 — Memory Ownership and Lifetime Patterns (0.8.6)

Load when designing data structures, choosing allocators (`mem`, `tmem`, `@stack_mem`, custom `Allocator`), writing teardown/rollback logic, or auditing C3 code for leaks and use-after-free bugs.

C3 has no RAII destructors or `unique_ptr`. Instead, ownership stays explicit and predictable through four patterns: allocator-driven lifetimes, flat containers with indices, `defer` / `defer catch`, and contract/runtime verification.

---

## 1. Choose Lifetime by Allocator

| Lifetime | Tool | Notes |
|---|---|---|
| Single call / loop iteration | `@pool()` + `tmem` | Bump-allocated scratch; reset in O(1) at `@pool()` exit |
| Small scratch with rare large spillover | `@stack_mem(N; Allocator smem)` | Stack buffer first, heap fallback freed automatically on exit |
| Subsystem / phase / request | Arena (`DynamicArenaAllocator`) or custom `Allocator` | Pass `Allocator` in; free the whole arena at phase end |
| Long-lived / cross-scope | `mem` (or caller's `Allocator`) | Freed explicitly via `defer` or owner's `.free()` / `.destroy()` |

### `@pool()` and `tmem` rules
- Reserve the `t*` prefix strictly for functions returning `tmem`-allocated data (matching stdlib: `string::tformat`, `file::load_temp`, `mem::temp_array`).
- **Always bound `tmem` inside `@pool() { ... };`**, especially inside loops and callbacks. Calling a `t*` helper without an enclosing `@pool()` leaks into the outer temp arena until the thread exits.
- Never return a `tmem` slice past its `@pool()` — copy only the winning/surviving result onto the caller's allocator before the pool closes.
- **Secondary OS threads** have no temp allocator until initialized: wrap thread entry points in `@pool_init(mem, 256 * 1024) { ... };`.

```c3
fn char[]? resolve_path(Allocator allocator, String dir, String name) {
    @pool() {
        String candidate = string::tformat("%s/%s", dir, name);
        if (!file::exists(candidate)) return NOT_FOUND~;
        // Copy only the surviving path out of the pool.
        return candidate.copy(allocator);
    };
}
```

### Small-buffer optimization with `@stack_mem`
Prefer `@stack_mem` over manual `char[N] stack; char* heap = null; defer if (heap != null) mem::free(heap);` splits:

```c3
// OnStackAllocator reserves an 8-byte header + up to 15-byte alignment slack,
// so add ~32 bytes over the target inline payload size.
const usz SCRATCH_STACK_BYTES = 256;

fn String escape_text(String input) {
    String err = "";
    @stack_mem(SCRATCH_STACK_BYTES; Allocator smem) {
        if (try buf = alloc::alloc_array_try(smem, char, input.len + 1)) {
            // Use buf.ptr / buf[..]; any heap spillover is freed at block exit.
        } else {
            err = "out of memory";
        }
    };
    return err;
}
```

- `OnStackAllocator.resize` (via `alloc::realloc_array_try(smem, ...)`) promotes stack buffers to the backing heap allocator automatically and tracks heap chunks for cleanup at block exit.
- **Macro-block `return` gotcha:** `return` inside `@pool() { ... };` or `@stack_mem(...) { ... };` returns from the **enclosing function**, not the macro block. Use `if (try ...)` to skip the rest of the block without returning early from the function.

---

## 2. Fallible vs Infallible Allocation & Zero-Init

- `mem::new_array(T, n)` and `mem::temp_array(T, n)` **zero-initialize** and return a slice (`T[]`), panicking on OOM. Don't follow them with `mem::clear`.
- `mem::alloc_array(T, n)` and `mem::talloc_array(T, n)` leave memory **uninitialized** — prefer them when you immediately overwrite every element (e.g., `dst[..] = src[:n]` or `mem::copy`).
- For OOM-safe code (parsers, runtimes, host boundaries), use the `*_try` forms on `alloc`:
  - `alloc::malloc_try(a, size)`
  - `alloc::alloc_array_try(a, T, n)` / `alloc::new_array_try(a, T, n)`
  - `alloc::realloc_array_try(a, ptr, T, n)`
- **Never cross allocator boundaries:** memory from `libc::malloc`/`realloc` must be freed with `libc::free`, never `mem::free` (and vice versa). Under the default `LIBC_ALLOCATOR` a mismatch can hide until `TrackingAllocator` (`mem::@assert_leak()`) or a custom allocator is enabled, where it corrupts accounting or crashes.

---

## 3. `defer`, `defer catch`, and Clean Ownership Transfer

### Block scoping
`defer` runs at the end of its **enclosing block**, not the enclosing function.
```c3
// BUG: frees immediately when the `if` block ends!
if (buf != null) defer mem::free(buf);

// Correct: defer lives in the outer block and checks the condition on exit.
defer if (buf != null) mem::free(buf);
```

### Partial-init rollback with `defer catch`
In optional-returning constructors, parsers, or decoders (`T*?`), attach `defer catch` right after each acquisition. Cleanup runs in LIFO order only when a fault is returned:

```c3
fn Resource*? Resource.create(Allocator a) {
    Resource* r = alloc::new_try(a, Resource)!;
    defer catch alloc::free(a, r);

    r.buf = alloc::alloc_array_try(a, char, 1024)!;
    defer catch alloc::free(a, r.buf.ptr);

    r.init_header()!;
    return r;
}
```

### Pointer-nulling transfer (avoid boolean `committed` flags)
When a non-optional function allocates a buffer that may either be discarded on error or handed off on success, null the local pointer on transfer:

```c3
char* buf = alloc::malloc_try(mem, n) ?? null;
if (buf == null) return false;
defer if (buf != null) mem::free(buf);

if (!fill(buf, n)) return false;

out.ptr = buf;
buf = null; // ownership transferred; defer becomes a no-op
return true;
```

### Grow-first / allocate-before-free
When growing, shrinking, or replacing an owned buffer, **allocate the new buffer before freeing the old one** (or grow the container before transferring ownership of an item into it). Freeing before allocating leaves a dangling pointer on OOM.

---

## 4. Flat Storage & Explicit Boundaries

- Prefer flat containers (`List{T}`, `Vec{T}`, arena slabs) + integer indices (`uint`) over pointer graphs or parallel raw arrays. One container owns the memory, indices stay valid across reallocation, and teardown is one `.free()`.
- Document pointer ownership at API boundaries with `<* ... *>` contracts:
  - `@param [&in] p` — borrowed read-only, non-null
  - `@param [&inout] p` — borrowed mutable, non-null
  - `@param [own] p` — callee takes ownership beyond the call
  - `@param [drop] p` — callee frees/invalidates `p` (e.g., `destroy` / `end` functions)
  - `@param [init] p` — callee initializes `*p`
- Keep `destroy()` and `reset()` teardown symmetric when a runtime/heap can be reset in place: every owned side table, registry, and GC root cleared in `destroy()` must also be released or reset in `reset()`.

---

## 5. Verification in Debug & Test Builds

- **`"VMEM_TEMP"` feature** (`-D VMEM_TEMP` or `"features": ["VMEM_TEMP"]` in `project.json` on `O0`/ASan targets): switches `tmem` to a `Vmem`-backed `TempAllocator` that page-protects unused regions (`protect_unused_pages` when `opt <= O1` or safe mode). Any escaped `tmem` read/write after `@pool()` exit faults immediately instead of silently reading stale stack/arena bytes.
- **`mem::@assert_leak()` + `"MEMORY_ASSERTS"`**: wraps `mem` in a `TrackingAllocator` and panics if any `mem` allocation outlives the block. Active in safe mode or with `"features": ["MEMORY_ASSERTS"]`. Prime one-time process globals outside the block, then run full create/use/error/destroy lifecycles inside it:
  ```c3
  mem::@assert_leak() {
      run_lifecycle_tests();
  };
  ```
- **Release-mode `assert` hazard:** in fast/unsafe builds (`-O2`+), `assert(...)` conditions are dropped. Never put side-effecting calls inside `assert(setup())`; assign the result first and check it separately (`int rc = setup(); assert(rc == 0);` or `if (rc != 0) unreachable("setup failed");`).
