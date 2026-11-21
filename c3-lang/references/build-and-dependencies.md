# C3 — Projects, Dependencies, and Packaging (0.8.6)

Load when editing `project.json`, choosing build or fetch commands, creating a `.c3l` library, or configuring target dependencies.

## Project commands

```bash
c3c init myproject
c3c build [target]
c3c run [target] -- [args...]
c3c test [target]
c3c benchmark [target]
c3c clean
c3c docgen
```

`c3c build` finds `project.json` by walking upward from the current directory. Use `c3c docgen` for generated API docs. The default project templates define `debug` and `release` targets.

## Target configuration

```json
{
  "targets": {
    "generate": {
      "type": "prepare",
      "exec": ["./generate_sources.sh"]
    },
    "my_lib": {
      "type": "static-lib",
      "depends-on": ["generate"]
    },
    "app": {
      "type": "executable",
      "depends-on": ["my_lib"],
      "safe": true,
      "opt": "O0",
      "env-override": ["C3_LOG_LEVEL=debug"]
    }
  }
}
```

Dependencies listed in `depends-on` build first, in order. `c3c build app --no-deps` skips them. `c3c clean` does not clean dependencies.

Target types include `executable`, `static-lib`, `dynamic-lib`, `source-lib`, `object-files`, `benchmark`, `test`, and `prepare`. `.ll` and `.bc` files can be included in `sources` alongside `.c3`, `.o`, and `.obj` files.

`project.json` strings expand `${NAME}` from the environment, except in `exec`, `exec-override`, `type`, `targets`, `vendor`, and `$schema`. Use `$${` for a literal `${`. Project-level `env` and target-level `env-override` contain `"NAME=value"` strings used by `exec` scripts. Scripts require `--trust=full`.

Other 0.8.6 settings include `features`, `function-sections`, `data-sections`, `stack-probe`, `stack-probe-size`, `stack-protector`, `debug-info`, `sanitize`, `trap-on-wrap`, `memory-env`, `fp-math`, `langrev`, `test-sources`, `dependency-search-paths`, and `max-vector-size`. Run `c3c --list-project-properties` for the authoritative list. `project.json5` supports comments.

Safe mode, not a target's name, controls runtime contract checks and bounds/null checks. `O0` and `O1` default to safe; `O2` and above default to unsafe. A custom target can set `"safe": true` explicitly.

Useful diagnostic features for `"features"` on debug/ASan/test targets:
- `"VMEM_TEMP"` — backs `tmem` with `Vmem` and page-protects unused regions (in `O0`/`O1` or safe mode), turning escaped `@pool()` reads/writes into immediate faults.
- `"MEMORY_ASSERTS"` — enables `mem::@assert_leak()` (`TrackingAllocator`) even on targets without full safe mode.

## Source libraries

A `source-lib` target packs C3 sources, C sources, and headers into a `.c3l` library usable on any platform:

```json
{
  "version": "0.1.0",
  "authors": ["Example Author"],
  "langrev": "1",
  "sources": ["src/**"],
  "c-sources": ["csource/*"],
  "c-include-dirs": ["csource/include"],
  "targets": {
    "my_lib": {
      "type": "source-lib"
    }
  }
}
```

```bash
c3c build my_lib
c3c source-lib src/my_lib.c3 src/extra.c3 -o my_lib
```

The output is compressed `<name>.c3l` by default. Use `"compress": false` in the target or `--no-compress` on the command line for a `.c3l` directory. The name may contain only lowercase letters, digits, and `_`. All files must be inside the project directory.

The generated `manifest.json` records `provides`, `dependencies`, `sources`, `c-sources`, `c-include-dirs`, `cc`, and `cflags`. Project libraries also record `version`, `authors`, and `langrev`. `linked-libraries` and `link-args` are not stored; use `@link` in source. A manifest without `targets` works on all platforms. Run `c3c --list-manifest-properties` for the full manifest schema.

## Fetching libraries

```bash
c3c fetch <library>
c3c project fetch [library ...]
c3c vendor-fetch <library>
```

`project fetch` with no arguments lists missing dependencies. With names, it fetches only those dependencies. `fetch`, `vendor-fetch`, and `project fetch` unpack into `<name>.c3l` directories by default; `--decompress=no` keeps the compressed file.

Registry downloads are verified against `checksum: "sha256:<hex>"`. Dependency entries may name a registry library as `[<url>:]<namespace>/<name>[@<version>]` and may lock a version as `<namespace>/<name>@<version>:<sha256>`. A registry version may provide its own download `url`. The build uses the library name, not the registry path. `fetch` adds only the name to `dependencies`.

Dependencies are found through dependency paths, the project's `fetch-url` / `--fetch-url`, or the default registry for a library's transitive dependencies. Scripts from a library manifest require `--trust=full`.

## Compiler flags added in 0.8.4 through 0.8.6

```text
--backend=c                         experimental C backend; --cflags <flag> forwards C flags
--function-sections=<yes|no>        one ELF section per function
--data-sections=<yes|no>            one ELF section per global
--implicit-float=<yes|no>           allow implicitly generated floating-point code
--stack-probe=<none|call|inline>    --stack-probe-size <bytes>
--stack-protector=<none|basic|strong|all>
--warn-unusedlocal=<yes|no|error>
--warn-unusedparam=<yes|no|error>
--keep-obj                          retain object files after linking
--stats=<none|summary|full|json>    --stats-file <path>
-gline-tables-only                  emit line tables only
--panicfn <function>                names a function; PanicFn supports formatted messages
--panic-msg=<yes|no>                --show-backtrace=<yes|no>
--infinite-loop-detect=<yes|no>     safe mode only, default no
--decompress=<yes|no>               default yes for fetched libraries
--no-compress                       uncompressed source-lib output
```

`--stats=full` replaces the removed `--print-large-functions`. `--panic-msg=no` traps only when `--show-backtrace=no` is also set; otherwise it prints a short message with file, function, and line. `--show-backtrace=no` omits that location information.
