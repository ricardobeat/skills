# C3 — Migrating from 0.7.x to 0.8.0

Load when reading, updating, or reviewing code written for C3 0.7.x. Skip when writing fresh 0.8.0 code — SKILL.md already uses the new names.

C3 0.8.0 was released on **2026-05-12**. Several APIs and language constructs were renamed or removed.

---

## Rename / removal table

| 0.7.x | 0.8.0 |
|-------|-------|
| `usz`, `isz` | `sz` (single signed-size type; implicit unsigned↔signed conversions removed) |
| `Type.sizeof`, `.alignof`, `.kindof` | `Type::size`, `Type::alignment`, `Type::kind` |
| `$sizeof(e)`, `$alignof(e)`, `$nameof(e)`, `$offsetof(T.f)` | `@sizeof(e)`, `@alignof(e)`, `$reflect(e).name`, `$reflect(T.f).offset` |
| `$typeof`, `$typefrom` | `$Typeof`, `$Typefrom` (capital T) |
| `$evaltype`, `$assignable`, `$is_const` | removed — use `$Typefrom`, `$defined($T x = e)`, etc. |
| `module foo <Type> { ... }` generic modules | only ad-hoc `struct Foo <Type>` |
| `Enum.elements`, `Enum.associated`, `Enum.lookup` | `Enum.len`, `Enum.membersof`, removed |
| `enum_a + enum_b` arithmetic | use `.ordinal`; `++`/`--` wrap-around still work |
| `@operator(!=)` | derived from `==`; add `@operator(<)` for ordering |
| `set_cursor` on streams | `seek` |
| `string.strip` / `strip_end` | `strip_prefix` / `strip_suffix` |
| `math::PI_2`, `PI_4`, `DIV_PI`, `cosec`, `cotan`, `muladd` | `HALF_PI`, `QUARTER_PI`, `INV_PI`, `csc`, `cot`, `mad` |
| `io::EOF?` (suffix `?`) | `io::EOF~` |
| `json::parse`, `parse_string` | `json::load`, `json::parse` |
| `Path` (unified) | `PathPosix` / `PathWin` (Path is implicit cast to String) |
| `@structlike` attribute | removed — distinct types are structlike by default |

---

## New in 0.8.0

- `@mustinit` attribute (forces zero-init at declaration)
- `SortedMap`, `Deque`, `OneShotChannel`
- Stable `mergesort`
- XML encoding, INI encoder, JSONC support, `docgen` command
- `$expand("expr")` — string-to-code
- `$reflect` for member/type reflection (`.name`, `.qname`, `.offset`, `.alignment`, `.size`)
- `untypedlist`
- Implicit unsigned↔signed integer conversions removed (must cast explicitly)
- `??` now binds tighter than `+ -`
