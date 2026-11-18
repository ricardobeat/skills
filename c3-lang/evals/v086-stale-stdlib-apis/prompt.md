---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Review this C3 0.8.6 snippet and list every API or behavior that is wrong, then show a corrected version. Do not assume that names from older C3 standard-library references still exist.

```c3
module audit;
import std::sort;
import std::core::string;
import std::crypto::rc4;
import std::io;

fn void main() {
    int[3] values = { 1, 2, 3 };
    sz? found = sort::binarysearch(values, 2);
    int? parsed = int::parse("42");
    char[3] key = "key";
    char[4] data = x"01020304";
    Rc4 stream;
    stream.init(key);
    stream.crypt(data[..], data[..], data.len);
    io::printfn("%d %d", found, parsed!!);
}
```

Compile the corrected version or explain precisely why the platform prevents compilation. `"42".to_int()` is valid on 0.8.6 because the integer base defaults to 10.
