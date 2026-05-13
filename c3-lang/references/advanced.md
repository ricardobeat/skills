# C3 — Advanced Features

Load when the task touches macros, generics, interfaces / dynamic dispatch, operator overloading, or contracts. Plain functions, structs, optionals, and stdlib usage don't need this file — they're covered by SKILL.md.

---

## Macros

```c3
// Basic macro (compile-time params use $ prefix)
macro max($Type)(a, b) {
    return a > b ? a : b;
}
max(int)(3, 5);  // → 5

// Unevaluated expression (#param) — argument is not evaluated before passing
macro measure(#expr) {
    sz start = clock();
    #expr;
    return clock() - start;
}
measure(some_expensive_fn());

// At-macros (@name) manage scopes
macro @swap(&a, &b) {
    var tmp = a;
    a = b;
    b = tmp;
}
@swap(x, y);

// Variadics (0.8.0): use $vaarg directly
macro sum($vaarg) {
    var total = 0;
    $for var $i = 0; $i < $vaarg.len; $i++:
        total += $vaarg[$i];
    $endfor
    return total;
}
```

Macros with only `$`-prefixed params execute entirely at compile time.

---

## Generics

```c3
// Ad-hoc generic type (the ONLY form in 0.8.0 — module-based generics removed)
struct Stack <Type> {
    sz capacity;
    sz size;
    Type* elems;
}

fn void Stack.push(Stack* self, Type element) { /* ... */ }
fn Type Stack.pop(Stack* self) { /* ... */ }

// Instantiation
alias IntStack = Stack{int};
IntStack s;
s.push(42);
int val = s.pop();

// Generic inference can now look through a pointer (0.8.0)
// Nested generics allowed inside generic functions/methods (0.8.0)
```

---

## Interfaces and Dynamic Dispatch

```c3
interface Drawable {
    fn void draw(self);
    fn void hover(self) @optional;   // implementations may omit this
}

struct Circle (Drawable) {    // Circle implements Drawable
    float radius;
}

fn void Circle.draw(Circle* self) @dynamic {
    io::printfn("Circle r=%f", self.radius);
}

// Dynamic dispatch via any type (typeid + void*)
fn void render(any obj) {
    Drawable d = (Drawable)obj;
    if (&d.draw) {    // check method exists at runtime
        d.draw();
    }
}

Circle c = { .radius = 5.0 };
render(&c);
```

---

## Operator Overloading

```c3
struct Vec2 { float x, y; }

fn Vec2 Vec2.add(self, Vec2 other) @operator(+) {
    return { self.x + other.x, self.y + other.y };
}

fn bool Vec2.equals(self, Vec2 other) @operator(==) {
    return self.x == other.x && self.y == other.y;
}

// Subscript
fn int List.get(self, sz idx) @operator([]) { return self.data[idx]; }
fn void List.set(self, sz idx, int val) @operator([]=) { self.data[idx] = val; }
```

Supported: `+ - * / % & | ^ ~ << >> == < <= [] []= &[] len`
0.8.0: `!=` is no longer overloadable (auto-derived from `==`). `<` enables full comparison overloads.

Variants:
- `@operator(+=)` — in-place form takes `&self` (pointer receiver) for mutation.
- `@operator_s` — symmetric (compiler may swap operand order).
- `@operator_r` — reverse-operand form (called when overload is on the RHS type).

---

## Contracts (Design by Contract)

```c3
<*
  @param n : "must be positive and under 1000"
  @require n > 0, n < 1000
  @ensure return > 0
*>
fn int process(int n) { return n * 10; }

fn int compute(int x) @pure { return x * x; }  // no side effects
```

In **safe mode** (`"safe": true` in project.json): contracts → runtime assertions.
In **fast mode**: contracts → optimizer hints (assumed true, no runtime cost).
Compile-time-evaluable contracts → always checked at compile time.
0.8.0: `:` before the description is now **mandatory** (`@param n : "..."`).
