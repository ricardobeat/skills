# C3 — Advanced Features

Load when the task touches macros, generics, interfaces/dynamic dispatch, operator overloading, or contracts.

---

## Macros

C3 macros are structured compile-time functions — no text substitution, no preprocessor. They operate within function scopes; top-level compile-time evaluation is intentionally restricted.

**Parameter sigils:**
- `$param` — compile-time constant or type (evaluated at call site)
- `#param` — unevaluated expression, bound to definition site; **evaluated every time it's used** — side effects repeat
- `regular` — runtime value, evaluated once before the call

Macros with `#` params or trailing `@body` blocks **must start with `@`** — visual signal of non-standard evaluation.

```c3
// Compile-time type param
macro max($Type)(a, b) {
    return a > b ? a : b;
}
max(int)(3, 5);  // → 5

// Unevaluated expression — called twice if used twice
macro @measure(#expr) {
    sz start = clock();
    #expr;
    return clock() - start;
}
measure(some_expensive_fn());

// At-macro with scope management
macro @swap(&a, &b) {
    var tmp = a;
    a = b;
    b = tmp;
}
@swap(x, y);

// Trailing body block
macro @foreach(a; @body(index, value)) {
    for (sz i = 0; i < a.len; i++) {
        @body(i, a[i]);
    }
}
@foreach(my_list; |idx, val| { io::printfn("%d: %s", idx, val); });

// Variadics
macro sum($vaarg) {
    var total = 0;
    $for var $i = 0; $i < $vaarg.len; $i++:
        total += $vaarg[$i];
    $endfor
    return total;
}
```

**Compile-time-only macros:** a macro with only `$`-prefixed params executes entirely at compile time.

---

## Generics

C3 generics use ad-hoc parameterization — no separate module-based generics.

**Type and constant parameters** — both supported:
```c3
struct Stack <Type> {
    sz capacity;
    sz size;
    Type* elems;
}

fn void Stack.push(Stack* self, Type element) { /* ... */ }
fn Type Stack.pop(Stack* self) { /* ... */ }

alias IntStack = Stack{int};
IntStack s;
s.push(42);
int val = s.pop();
```

**Constant parameters** (int, bool, enum) enable compile-time dimensions:
```c3
struct Matrix <Type, int ROWS, int COLS> {
    Type[ROWS * COLS] data;
}
alias Mat4f = Matrix{float, 4, 4};
```

**Grouping:** generics with identical parameter names in the same module auto-instantiate together. Different names create separate groups.

**Constraints** via `@require`:
```c3
<*
 @require $assignable(Type, int)
*>
fn Type sum_all <Type>(Type[] arr) {
    Type total = 0;
    foreach (v : arr) total += v;
    return total;
}
```

**Extending specific instantiations** — possible but loses access to generic params:
```c3
fn String IntStack.to_string(&self) { /* only works on Stack{int} */ }
```

**Generic inference** can look through pointers (0.8.0). Nested generics inside generic functions/methods are allowed.

---

## Interfaces and Dynamic Dispatch

C3 interfaces use dynamic dispatch similar to Objective-C — runtime method lookup via `any` (typeid + void*).

```c3
interface Drawable {
    fn void draw(self);
    fn String name(self) @optional;   // implementations may omit this
}

struct Circle (Drawable) { float radius; }

fn void Circle.draw(&self) @dynamic {
    io::printfn("Circle r=%f", self.radius);
}
fn String Circle.name(&self) @dynamic { return "circle"; }
```

**Dynamic dispatch via `any`:**
```c3
fn void render(any obj) {
    Drawable d = (Drawable)obj;      // cast any → interface
    d.draw();                        // dispatches at runtime
}

Circle c = { .radius = 5.0 };
render(&c);
```

**Check optional methods before calling:**
```c3
if (&d.name) {
    io::printn(d.name());
}
```

**Subtype inheritance** via inline members:
```c3
struct ColorCircle (Drawable) {
    inline Circle base;   // inherits Circle's Drawable implementation
    int color;
}
```

**Explicit any varargs** (pointer passing required):
```c3
fn void vaargfn(int x, any... args) { ... }
vaargfn(2, &b, &&3.0);   // must pass pointers explicitly
```

**Implicit any varargs** (auto-pointer, but don't mutate):
```c3
fn void vaanyfn(int x, args...) { ... }
vaanyfn(2, b, 3.0);      // pointers created automatically — don't mutate args
```

**Runtime type checking:**
```c3
fn void inspect(any val) {
    switch (val.type) {
        case int.typeid:  io::printfn("int: %d", *(int*)val.ptr);
        case float.typeid: io::printfn("float: %f", *(float*)val.ptr);
    }
    // or via anycast:
    if (try n = anycast(val, int)) { io::printfn("got int %d", n); }
}
```

---

## Operator Overloading

```c3
struct Vec2 { float x, y; }

fn Vec2 Vec2.add(self, Vec2 other) @operator(+)  { return { self.x+other.x, self.y+other.y }; }
fn bool Vec2.equals(self, Vec2 other) @operator(==) { return self.x==other.x && self.y==other.y; }
fn bool Vec2.less(self, Vec2 other) @operator(<) { return self.x < other.x; }
// Implementing < and == gives you <=, !=, >=, > automatically
// != is NOT separately overloadable — auto-derived from ==
```

**Container operators:**
```c3
fn int  List.get(self, sz idx)           @operator([])   { return self.data[idx]; }
fn void List.set(self, sz idx, int val)  @operator([]=)  { self.data[idx] = val; }
fn int* List.ref(self, sz idx)           @operator(&[])  { return &self.data[idx]; }  // enables foreach &
fn sz   List.len(self)                   @operator(len)  { return self.size; }         // enables ^n indexing + foreach
```

**Symmetric and reverse operators:**
```c3
// @operator_s — both `Complex + double` and `double + Complex` work
fn Complex Complex.add_scalar(self, double d) @operator_s(+) { ... }

// @operator_r — called when this type is on the RHS
fn Complex Complex.radd(self, double d) @operator_r(+) { ... }
```

**In-place forms** take pointer receiver:
```c3
fn void Vec2.add_assign(&self, Vec2 other) @operator(+=) { self.x += other.x; self.y += other.y; }
```

Supported: `+ - * / % & | ^ ~ << >> == < <= [] []= &[] len`

Operators should keep their conventional meaning — overloading `+` for something other than addition creates confusing code.

---

## Contracts

Pre/post-condition checks. Compilers may use them for static analysis, runtime assertions, or optimizer hints. Violating a contract is **unspecified behavior**.

```c3
<*
  @param n : "must be positive and under 1000"
  @require n > 0 && n < 1000
  @ensure return > 0
*>
fn int process(int n) { return n * 10; }

fn int compute(int x) @pure { return x * x; }  // no side effects, no global reads/writes
```

**Pointer parameter annotations** (inside `<*...*>` contract block):
```c3
<*
 @param [&out] dst
 @param [&in] src
*>
fn void copy(int* dst, int* src, sz len) { ... }
// [in]    — pointer is only read
// [out]   — pointer is only written
// [inout] — both
// & prefix — also asserts non-null
```

**Behavior by mode:**
- **Safe mode** (`"safe": true` in project.json): `@require` → runtime assertion
- **Release mode**: contracts → optimizer hints (assumed true, zero cost)
- Compile-time-evaluable contracts → always checked at compile time

`c3c` currently checks: compile-time constant validation, runtime `@require` assertions, and caller-side verification.

> Contracts don't prevent aliasing violations — a `[in]` pointer can still be written through an alias. They're advisory, not enforced by the type system.
