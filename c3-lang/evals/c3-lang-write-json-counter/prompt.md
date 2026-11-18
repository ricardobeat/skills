---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Write a complete C3 0.8.6 program that reads a JSON file whose path is argv[1], iterates its top-level array, counts entries whose `status` field equals "done", and prints the total. Handle a missing argument, a missing file, and JSON parse errors with distinct useful messages; exit with code 1 on failure. Use the temp allocator for the parse, handle every optional, and show the full file with module declaration and imports. Verify it with `c3c compile-run` and a small fixture.
