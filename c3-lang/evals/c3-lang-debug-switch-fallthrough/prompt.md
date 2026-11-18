---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Why does this print only "Not done", never "Done", even when I pass DONE? I am coming from C and expected it to fall through.

```c3
module app;
import std::io;

enum Status : uint { IDLE, BUSY, DONE }

fn void report(Status s) {
    switch (s) {
        case IDLE:
        case BUSY:
            io::printn("Not done");
        case DONE:
            io::printn("Done");
    }
}

fn void main() {
    report(DONE);
}
```

Answer for C3 0.8.6 and compile the example if that helps check the premise.
