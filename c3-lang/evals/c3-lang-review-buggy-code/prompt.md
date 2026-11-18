---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Review this C3 0.8.6 code and list every bug or issue you can spot. Do not rewrite it yet.

```c3
module app;
import std::io;
import libc;

fn String? read_name(String path) {
    return file::load_temp(path);
}

fn int main() {
    String name = read_name("name.txt");
    char[64] buf;
    libc::strcpy(buf, name.ptr);

    usz total = name.len + int::size;
    io::printfn("name=%s len=%d", name, total);
    return 0;
}
```

`fn int main()`, `usz`, and `int::size` are valid in 0.8.6. Do not flag them as defects.
