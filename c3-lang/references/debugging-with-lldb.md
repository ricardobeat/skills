# Debugging C3 with LLDB

C3 compiles through LLVM, producing native binaries with DWARF debug info. This means standard LLDB workflows apply, with some C3-specific naming conventions and type behaviors.

## Building for Debug

```bash
# Single file — quickest way to get a debug binary (debug info is automatic at -O0)
c3c compile -O0 -o myapp src/main.c3

# Project build — just build the debug target
c3c build debug                    # specific target
c3c build                          # all targets
```

`-O0` through `-O5` emit DWARF debug info automatically — no `-g` flag needed. `-g` is only required with `-Os`/`-Oz` (which strip debug info by default). For stepping accuracy, prefer `-O0`: no inlining, no reordering, all locals visible at every line.

**Recommended `project.json` debug target:**
```json
{
  "targets": {
    "debug":   { "type": "executable", "opt": "O0" },
    "release": { "type": "executable", "opt": "O3", "strip-unused": true }
  }
}
```

Build with `c3c build debug`, then `lldb out/debug`.

---

## Symbol Naming

C3 compiles to LLVM symbols using the pattern `_module.symbol`. LLDB resolves names without the leading underscore.

| C3 source | LLDB symbol | Example |
|-----------|-------------|---------|
| `fn void main()` in module `myapp` | `myapp.main` | `breakpoint set -n myapp.main` |
| `fn int divide(int a, int b)` in module `myapp` | `myapp.divide` | `breakpoint set -n myapp.divide` |
| `fn int Point.dist(&self)` in module `myapp` | `myapp.Point.dist` | `breakpoint set -n myapp.Point.dist` |
| Short name (if unambiguous) | `divide` | `breakpoint set -n divide` |

The runtime generates a C-level `main` entry point (in `main_stub.c3`) that calls your module's `main`. In backtraces you'll see both — your function appears as `module.main`.

---

## Launching LLDB

```bash
# Attach to a compiled binary
lldb out/debug

# Or compile and debug in one step
c3c compile -O0 -o myapp src/main.c3 && lldb myapp
```

Inside LLDB:
```
(lldb) run                          # start the program
(lldb) run arg1 arg2                # with arguments
(lldb) run < input.txt              # with stdin redirect
```

---

## Breakpoints

### By function name

```
(lldb) breakpoint set -n myapp.divide
Breakpoint 1: where = myapp`myapp.divide + 36 at main.c3:18:6

(lldb) breakpoint set -n myapp.Point.manhattan
Breakpoint 2: where = myapp`myapp.Point.manhattan + 16 at main.c3:9:31
```

**Tip:** Breakpoints on function names stop at the function signature line, where local variables may not be initialized yet. Set breakpoints on specific lines inside the body instead. Also, function-name breakpoints may not fire at `-O1` and above if the compiler inlines the function — stick to `-O0` for predictable breakpoint behavior.

### By file and line

```
(lldb) breakpoint set -f main.c3 -l 10
Breakpoint 3: where = myapp`myapp.Point.manhattan + 32 at main.c3:10:11
```

This stops at the actual statement, where variables are live.

### Conditional breakpoints

```
(lldb) breakpoint set -n myapp.divide -c 'b == 0'
(lldb) breakpoint set -f main.c3 -l 42 -c 'catch err != 0'
```

### Managing breakpoints

```
(lldb) breakpoint list                # show all breakpoints
(lldb) breakpoint disable 1           # temporarily disable
(lldb) breakpoint enable 1            # re-enable
(lldb) breakpoint delete 1            # remove
(lldb) breakpoint delete              # remove all
```

---

## Stepping

| Command | Short | Behavior |
|---------|-------|----------|
| `next` | `n` | Step over (execute function calls without entering) |
| `step` | `s` | Step into (enter function calls) |
| `finish` | `f` | Step out (run until current function returns) |
| `continue` | `c` | Resume until next breakpoint/watchpoint |
| `nexti` | `ni` | Step one instruction (assembly level) |
| `stepi` | `si` | Step one instruction, entering calls |

```
(lldb) n                            # next line
(lldb) s                            # step into called function
(lldb) f                            # finish current function, show return value
(lldb) c                            # continue to next breakpoint
```

`finish` shows the return value, including for optional returns:
```
(lldb) finish
Process stopped
Return value: (int) $0 = 3
```

---

## Inspecting Variables

### Local variables

```
(lldb) frame variable               # all locals in current frame
(lldb) frame variable a             # specific variable
(lldb) frame variable a b total     # multiple variables
```

Output maps directly to C3 types:
```
(int) a = 10
(int) b = 3
(int) result = 3
(String[]) args = { ptr = 0x00000001006dc6a0, len = 1 }
```

### Struct members

```
(lldb) frame variable p
(Point) p = { x = 1, y = -2 }

(lldb) frame variable p.x
(int) p.x = 1
```

### Pointer receiver (`&self`) in methods

C3 passes `&self` as a pointer. Use `->` to access members:

```
(lldb) frame variable self
(Point *) self = 0x000000016fdfd1e8

(lldb) p *self                      # dereference to see full struct
(Point) { x = 1, y = -2 }

(lldb) p self->x                    # access member via pointer
(int) 1

(lldb) p self->y
(int) -2
```

### Arrays and slices

```
(lldb) frame variable pts
(Point[3]) pts = ([0] = Point @ 0x..., [1] = Point @ 0x..., [2] = Point @ 0x...)

(lldb) frame variable arr
(int[]) arr = { ptr = 0x..., len = 5 }
```

### Expressions

```
(lldb) p a + b                      # evaluate expressions
(int) 13

(lldb) p sizeof(Point)              # type size
(unsigned long) 8

(lldb) p (Point){3, 4}              # cast/construct values
(Point) { x = 3, y = 4 }
```

---

## Watchpoints

Watchpoints trigger when a variable's value changes (hardware-assisted, typically 4 available):

```
(lldb) breakpoint set -n myapp.process_points
(lldb) run
# ... hit breakpoint ...
(lldb) watchpoint set variable total
Watchpoint created: Watchpoint 1

(lldb) c
# stops when 'total' changes:
Watchpoint 1 hit:
old value: 0
new value: 3

(lldb) frame variable total
(int) total = 3
```

---

## Backtrace

```
(lldb) bt
* thread #1, stop reason = breakpoint 1.1
  * frame #0: myapp`myapp.divide(a=10, b=0) at main.c3:18:6
    frame #1: myapp`myapp.main(args=String[] @ 0x...) at main.c3:41:14
    frame #2: myapp`@main_args at main_stub.c3:28:10 [inlined]
    frame #3: myapp`main(.anon=1, .anon=0x...) at main.c3:33:8
```

- `frame #0` is where the breakpoint hit
- `frame #1` is your C3 `main` function
- `frame #2-3` are the C3 runtime entry point (not your code)

Navigate frames:
```
(lldb) frame select 1               # switch to frame #1
(lldb) up                           # one frame up
(lldb) down                         # one frame down
```

---

## C3-Specific Behaviors in LLDB

### Optionals (`T?`)

Optionals appear as their underlying type in LLDB. An uninitialized optional may show garbage:

```
(int) safe = 2                      # optional int — value present
(int) safe = 0                      # could be zero-value or uninitialized
```

To check if an optional holds a fault, use `@catch` or `@ok` in C3 source — LLDB shows the raw internal representation.

### Fault values

Faults appear as pointer-sized integers in LLDB:

```
(fault) err = 12370743968           # raw fault identifier
```

The symbolic name (e.g., `DIVISION_BY_ZERO`) is available in C3 source via `@catch` but not directly in LLDB expressions.

### `self` in methods

Methods with `&self` pass a pointer. In LLDB:
- `frame variable self` shows the pointer
- `p *self` shows the dereferenced struct
- `p self->member` accesses members

Methods with value receiver `self` (no `&`) show `self` as a value type directly.

### `foreach` loop variables

`foreach` loop variables appear in `frame variable` output, including an internal `.temp` iterator (harmless, ignore it):

```
(sz) .temp = 0                      # internal loop iterator (ignore)
(int) i = 0                         # your index variable
(Point) p = { x = 1, y = -2 }      # your loop variable
(int) m = 3                         # variable inside loop body
```

### Runtime frames

C3 programs include a runtime entry point (`main_stub.c3`). Your `main` appears as `module.main` in backtraces, one frame below the generated `main`. On macOS, one additional `dyld` frame appears at the very bottom (the dynamic linker entry point).

### SIGTRAP on panics

C3 uses trap instructions for panics and contract violations. LLDB always stops on these — this is usually what you want, since the trap location shows exactly what went wrong.

**Linux:** The trap arrives as a POSIX `SIGTRAP` signal. If you need to let the process continue (rare), use:
```
(lldb) process handle --pass true --stop false SIGTRAP
```

**macOS:** The trap arrives as a Mach exception (`EXC_BREAKPOINT`), not a POSIX signal. `process handle SIGTRAP` has no effect. LLDB always stops on Mach-level traps — there is no built-in way to suppress them.

Avoid adding `--stop false SIGTRAP` to `~/.lldbinit` permanently — it would silence all panic stops on Linux, robbing you of the primary debugging signal for crashes.

---

## Common Workflows

### Debug a crash

```bash
c3c build debug
lldb out/myapp
(lldb) run                          # run until crash
(lldb) bt                           # see where it crashed
(lldb) frame variable               # inspect local state
```

### Debug an optional/fault path

```
(lldb) breakpoint set -n myapp.divide
(lldb) run
(lldb) frame variable a b           # inspect inputs
(lldb) n                            # step past the check
(lldb) frame variable               # see which branch was taken
(lldb) c                            # continue
```

### Step through a method

```
(lldb) breakpoint set -f main.c3 -l 10   # line inside method body
(lldb) run
(lldb) p *self                      # inspect receiver
(lldb) n                            # step through
(lldb) frame variable mx my         # inspect computed values
(lldb) f                            # finish, see return value
```

### Debug with watchpoint

```
(lldb) breakpoint set -n myapp.process_points
(lldb) run
(lldb) watchpoint set variable total
(lldb) c                            # stops every time total changes
(lldb) bt                           # see what changed it
```

### Attach to running process

```
(lldb) process attach --name myapp
(lldb) bt                           # see where it's stuck
(lldb) process detach
```

---

## LLDB Quick Reference

| Task | Command |
|------|---------|
| Run | `run` |
| Run with args | `run arg1 arg2` |
| Continue | `c` |
| Step over | `n` |
| Step into | `s` |
| Step out (show return) | `f` |
| All locals | `frame variable` |
| Specific var | `frame variable name` |
| Struct member | `frame variable p.x` |
| Dereference self | `p *self` |
| Pointer member | `p self->x` |
| Evaluate expr | `p expr` |
| Backtrace | `bt` |
| Switch frame | `frame select N` |
| Break by name | `breakpoint set -n name` |
| Break by line | `breakpoint set -f file.c3 -l N` |
| Conditional | `breakpoint set -n name -c 'expr'` |
| Watch variable | `watchpoint set variable name` |
| List breakpoints | `breakpoint list` |
| Delete all | `breakpoint delete` |
| Frame up | `up` |
| Frame down | `down` |
| Find symbols | `image lookup -rn 'pattern'` |
| List all symbols | `image dump symtab` |
| Disassemble | `disassemble` |
| Register read | `register read` |
