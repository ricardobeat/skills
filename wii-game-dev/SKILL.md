---
name: wii-game-dev
description: use to develop custom  games for the Wii gaming console; devkitpro; homebrew games
---

# Homebrew game development for the Wii

## Overview

How to get started and compile a game for the Wii. 

## Installing tools on Mac

Based on https://devkitpro.org/wiki/Getting_Started.

1. Download latest .pkg installer from https://github.com/devkitPro/pacman/releases/latest
2. Install pkg
3. setup packages with `dkp-pacman` in the terminal:

```sh
sudo dkp-pacman -S wii-dev
sudo chown -R $(whoami):staff /opt/devkitpro
```

4. Install GRRLIB graphics library

```sh
# install dependencies using devkitpro's pacman package manager
sudo dkp-pacman -S --needed ppc-libpng ppc-freetype ppc-libjpeg-turbo libfat-ogc

# clone grrlib repository and install lib files
git clone https://github.com/GRRLIB/GRRLIB
make -C GRRLIB clean all install
```

## Development

Start by copying the Makefile from `assets/Makefile` into your project directory.

Minimal code for `source/main.c`:

```c
#include <grrlib.h>
#include <stdlib.h>
#include <wiiuse/wpad.h>

int main(int argc, char **argv) {
    GRRLIB_Init();
    WPAD_Init();

    while(SYS_MainLoop()) {
        WPAD_ScanPads();  // Scan the Wiimotes
        if (WPAD_ButtonsDown(0) & WPAD_BUTTON_HOME)  break;

        // Place your drawing code here

        GRRLIB_Render();  // Render the frame buffer to the TV
    }
    GRRLIB_Exit(); // Be a good boy, clear the memory allocated by GRRLIB
    exit(0);  // Use exit() to exit a program, do not use 'return' from main()
}
```

- See `$GRRLIB/examples/*` for more complete examples

## Notes

- Use `DEVKITPPC` for the Wii
- always build to verify with `make`

You might need these env vars to be able to run `make` from within your sandbox:

```sh
export DEVKITPRO=/opt/devkitpro
export DEVKITPPC=${DEVKITPRO}/devkitPPC
export PKG_CONFIG_PATH=${DEVKITPRO}/portlibs/wii/lib/pkgconfig
export PKG_CONFIG_LIBDIR=${DEVKITPRO}/portlibs/wii/lib/pkgconfig
export PKG_CONFIG=powerpc-eabi-pkg-config
export PATH=$DEVKITPPC/bin:$PATH
```

## Running

The [Dolphin](https://dolphin-emu.org) emulator can be installed via Homebrew: `brew install --cask dolphin` and used to
load the compiled `.dol` game files. Use it to test locally before copying to an SD card to run on the Wii hardware.

## References

- [GRRLIB API reference](references/grrlib.md) — full function signatures for GRRLIB 4.6.1
- more examples for native code at `/opt/devkitpro/examples/wii/` (load only if strictly necessary)
