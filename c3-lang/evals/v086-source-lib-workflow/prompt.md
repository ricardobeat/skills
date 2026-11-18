---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Create a minimal C3 0.8.6 `project.json` with a `source-lib` target named `mylib`, a `static-lib` target that depends on `mylib`, and an executable target depending on the static library. Include `version`, `authors`, `langrev`, `sources`, and `depends-on` keys where appropriate. Then give the commands to build the source library, build the app with dependencies, build only the selected app target, and fetch one named dependency. Use `c3c --list-project-properties` to verify the keys and explain the default `.c3l` output and checksum behavior.
