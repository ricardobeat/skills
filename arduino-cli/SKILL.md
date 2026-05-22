---
name: arduino-cli
description: microcontroller projects using arduino-cli and justfile. Covers ESP32/M5Stack/LilyGo boards, common commands (build/upload/monitor/libs), FQBN lookup, port detection, library management, and LittleFS. Use whenever the user is working in a project with a justfile + arduino-cli setup, asks about compiling/uploading/monitoring Arduino sketches, or needs board/library configuration.
---

# Arduino CLI + Justfile Workflow

## Core Principle

**Always prefer `just <task>` over bare `arduino-cli` commands.** The justfile is the canonical interface — it encodes board config, port globs, and extra flags so they don't need to be repeated. Only call `arduino-cli` directly when no justfile task covers the operation.

Also prefer searching online documentation and examples over reading the local arduino-cli library cache (under `~/Library/Arduino15/libraries/`).

---

## Justfile Patterns

A minimal project justfile looks like:

```justfile
set dotenv-load

# Board FQBN — encode here, not scattered in commands
FQBN := "esp32:esp32:m5stack_stickc_plus2"
PORT := "/dev/cu.usbserial-*"

default: build upload

libs:
    arduino-cli lib install "M5GFX"
    arduino-cli lib install "M5Unified"

build:
    arduino-cli compile --fqbn "{{FQBN}}"

upload: build
    arduino-cli upload --fqbn "{{FQBN}}" --port {{PORT}}

monitor:
    arduino-cli monitor --port {{PORT}} --config baudrate=115200
```

Key conventions:
- `default: build upload` — running `just` compiles and flashes in one step
- `upload: build` — upload depends on build so `just upload` always recompiles
- Port is a glob; arduino-cli resolves it to the first match
- `set dotenv-load` — loads a `.env` file if present (useful for secrets/config)

---

## Common Boards & FQBNs

| Board | FQBN | Port glob |
|-------|------|-----------|
| M5StickC Plus2 | `esp32:esp32:m5stack_stickc_plus2` | `/dev/cu.usbserial-*` |
| LilyGo T-QT Pro (ESP32-S3 N8) | `esp32:esp32:esp32s3:FlashSize=8M,PartitionScheme=default_8MB,PSRAM=disabled` | `/dev/cu.usbmodem*` |
| Generic ESP32 | `esp32:esp32:esp32` | `/dev/cu.usbserial-*` |
| ESP32-S3 (generic) | `esp32:esp32:esp32s3` | `/dev/cu.usbmodem*` |

To look up an FQBN interactively: `arduino-cli board listall` or `arduino-cli board details --fqbn <fqbn>`.

Install the ESP32 core if missing:
```
arduino-cli core install esp32:esp32
```

---

## Library Management

Install libraries by name (must match Arduino Library Manager name exactly):
```
arduino-cli lib install "M5GFX"
arduino-cli lib install "M5Unified"
arduino-cli lib install "M5StickCPlus2"
arduino-cli lib install "ArduinoJson"
arduino-cli lib install "WebSockets"
arduino-cli lib install "LovyanGFX"
arduino-cli lib install "ESP8266Audio"
```

Search for a library: `arduino-cli lib search <keyword>`

Installed libraries live at `~/Library/Arduino15/libraries/` on macOS — browse for reference, but prefer online docs.

---

## LittleFS (filesystem image)

When a project serves files from flash (sounds, HTML, etc.):

```justfile
make-fs:
    mklittlefs -c ./data -b 4096 -p 256 -s 0x180000 littlefs.bin

upload-fs:
    esptool --baud 2000000 write-flash 0x670000 littlefs.bin

files: make-fs upload-fs
```

Partition offset (`0x670000`) and size (`0x180000`) come from the partition table (`partitions.csv`). Adjust when changing partition schemes.

---

## arduino-cli.yaml Location

macOS: `~/Library/Arduino15/arduino-cli.yaml`

Add the M5Stack board index there if it's missing:
```yaml
board_manager:
  additional_urls:
    - https://static-cdn.m5stack.com/resource/arduino/package_m5stack_index.json
    - https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

---

## Useful One-liners (call directly when no justfile task exists)

```bash
# List connected boards
arduino-cli board list

# Show board details / available options
arduino-cli board details --fqbn "esp32:esp32:m5stack_stickc_plus2"

# Compile with verbose output (debug build errors)
arduino-cli compile --fqbn <fqbn> -v

# Monitor with specific baud rate
arduino-cli monitor --port /dev/cu.usbserial-* --config baudrate=115200

# Update library index
arduino-cli lib update-index
```

---

## Troubleshooting

- **Port not found** — check `arduino-cli board list`; make sure the USB driver is loaded and the cable supports data (not charge-only).
- **Upload fails after compile** — try pressing the reset button on the board just before upload starts (some boards need manual boot mode).
- **`esp32s3` board with USB CDC** — port shows as `/dev/cu.usbmodem*` not `/dev/cu.usbserial-*`; update the PORT variable in the justfile.
- **Library not found at compile time** — run the `libs` justfile task, then retry `just build`.
- **Wrong FQBN options** — run `arduino-cli board details --fqbn <base-fqbn>` to see all available option keys and values.
