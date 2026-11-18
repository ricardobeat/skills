---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Write a complete C3 0.8.6 program that declares two excuse values with `excuse`, defines an `attrmacro` bundle, declares a generic `Box<Type>` struct, and returns a `Box{int}` value from a generic function. Use `@feat(POSIX | !WIN32)` for one top-level function and `$if` only inside a function body. Handle a returned optional with `if (catch)`, then compile the file with `c3c compile-only`. Explain which forms would be wrong in C3 0.8.3.
