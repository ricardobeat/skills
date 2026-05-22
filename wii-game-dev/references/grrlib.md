# GRRLIB 4.6.1 Quick Reference

C/C++ 2D/3D graphics library for Wii. Wraps Nintendo GX. Include: `#include <grrlib.h>`

**Docs:** https://grrlib.github.io/GRRLIB/  
**Repo:** https://github.com/GRRLIB/GRRLIB

---

## Lifecycle

```c
int  GRRLIB_Init(void)        // init; returns 0 on success
void GRRLIB_Exit(void)        // shutdown + free all resources
void GRRLIB_Render(void)      // flush GX pipeline, flip framebuffer (call each frame)
```

---

## Color

```c
// All colors are u32 RGBA (R in MSB)
#define RGBA(r,g,b,a)   // pack components
#define R(c)            // extract red
#define G(c)            // extract green
#define B(c)            // extract blue
#define A(c)            // extract alpha
```

Common values: `0xFF0000FF`=red, `0x00FF00FF`=green, `0x0000FFFF`=blue, `0xFFFFFFFF`=white, `0x000000FF`=black

---

## Data Structures

```c
typedef struct {
    u32   w, h;           // dimensions
    u32   format;         // GX texture format
    int   handlex, handley;
    bool  tiledtex;
    u32   tilew, tileh, nbtilew, nbtileh, tilestart;
    void *data;
} GRRLIB_texImg;

typedef struct {
    void *face;     // FreeType FT_Face
    bool  kerning;
} GRRLIB_Font;     // used as GRRLIB_ttfFont*

typedef struct {
    u8  width, height;
    s8  relx, rely;
    u8  kerning;
    u8 *data;
} GRRLIB_bytemapChar;

typedef struct {
    char              *name;
    u32               *palette;
    u16                nbChar;
    u8                 version;
    s8                 tracking;
    GRRLIB_bytemapChar charDef[256];
} GRRLIB_bytemapFont;

typedef struct {
    bool             antialias;
    GRRLIB_blendMode blend;
    int              lights;
} GRRLIB_drawSettings;
```

---

## 2D Primitives

```c
void GRRLIB_FillScreen(const u32 color)
void GRRLIB_Plot(const f32 x, const f32 y, const u32 color)
void GRRLIB_Line(const f32 x1, const f32 y1, const f32 x2, const f32 y2, const u32 color)
void GRRLIB_Rectangle(const f32 x, const f32 y, const f32 w, const f32 h, const u32 color, const bool filled)
void GRRLIB_Circle(const f32 x, const f32 y, const f32 radius, const u32 color, const u8 filled)
void GRRLIB_Ellipse(const f32 x, const f32 y, const f32 rx, const f32 ry, const u32 color, const u8 filled)

// Multi-point
void GRRLIB_NPlot(const guVector v[], const u32 color[], const u16 n)       // point array
void GRRLIB_NGone(const guVector v[], const u32 color[], const u16 n)       // polygon outline
void GRRLIB_NGoneFilled(const guVector v[], const u32 color[], const u16 n) // filled polygon
```

---

## Textures

### Load / Create
```c
GRRLIB_texImg* GRRLIB_LoadTexture(const u8 *my_img)                          // auto-detect PNG/JPG/BMP/TPL
GRRLIB_texImg* GRRLIB_LoadTexturePNG(const u8 *my_png)
GRRLIB_texImg* GRRLIB_LoadTextureJPG(const u8 *my_jpg)
GRRLIB_texImg* GRRLIB_LoadTextureJPGEx(const u8 *my_jpg, const u32 size)
GRRLIB_texImg* GRRLIB_LoadTextureBMP(const u8 *my_bmp)                       // uncompressed only
GRRLIB_texImg* GRRLIB_LoadTextureTPL(const u8 *my_tpl, u32 id)
GRRLIB_texImg* GRRLIB_LoadTextureFromFile(const char *filename)               // from SD card
GRRLIB_texImg* GRRLIB_CreateEmptyTexture(const u32 w, const u32 h)           // GX_TF_RGBA8
GRRLIB_texImg* GRRLIB_CreateEmptyTextureFmt(const u32 w, const u32 h, const u32 format)
```

### Manage
```c
void GRRLIB_FreeTexture(GRRLIB_texImg *tex)
void GRRLIB_FlushTex(GRRLIB_texImg *tex)       // flush CPU cache → main mem (required after pixel writes)
void GRRLIB_ClearTex(GRRLIB_texImg *tex)       // clear to transparent black + flush
```

### Pixel Access
```c
u32  GRRLIB_GetPixelFromtexImg(const int x, const int y, const GRRLIB_texImg *tex)
void GRRLIB_SetPixelTotexImg(const int x, const int y, GRRLIB_texImg *tex, const u32 color) // call FlushTex after
u32  GRRLIB_GetPixelFromFB(int x, int y)
void GRRLIB_SetPixelToFB(int x, int y, u32 color)
```

### Handle (rotation origin)
```c
void GRRLIB_SetHandle(GRRLIB_texImg *tex, const int x, const int y)
void GRRLIB_SetMidHandle(GRRLIB_texImg *tex, const bool enabled) // center handle
```

---

## Drawing Textures

```c
// pos=(x,y), degrees=rotation, scaleX/Y=scale, color=tint (use 0xFFFFFFFF for none)
void GRRLIB_DrawImg(const f32 x, const f32 y, const GRRLIB_texImg *tex,
                    const f32 degrees, const f32 scaleX, const f32 scaleY, const u32 color)

void GRRLIB_DrawImgQuad(const guVector pos[4], GRRLIB_texImg *tex, const u32 color)

// frame = tile index within tileset
void GRRLIB_DrawTile(const f32 x, const f32 y, const GRRLIB_texImg *tex,
                     const f32 degrees, const f32 scaleX, const f32 scaleY,
                     const u32 color, const int frame)

void GRRLIB_DrawTileQuad(const guVector pos[4], GRRLIB_texImg *tex, const u32 color, const int frame)

// draw sub-region: partx/y = source offset, partw/h = source size
void GRRLIB_DrawPart(const f32 x, const f32 y, const f32 partx, const f32 party,
                     const f32 partw, const f32 parth, const GRRLIB_texImg *tex,
                     const f32 degrees, const f32 scaleX, const f32 scaleY, const u32 color)
```

### Tileset Setup
```c
void GRRLIB_InitTileSet(GRRLIB_texImg *tex, const u32 tilew, const u32 tileh, const u32 tilestart)
```

---

## Bitmap Effects (BMFX)

All effects write to a separate dest texture. Call `GRRLIB_FlushTex(texdest)` after.

```c
void GRRLIB_BMFX_FlipH(const GRRLIB_texImg *src, GRRLIB_texImg *dst)
void GRRLIB_BMFX_FlipV(const GRRLIB_texImg *src, GRRLIB_texImg *dst)
void GRRLIB_BMFX_Grayscale(const GRRLIB_texImg *src, GRRLIB_texImg *dst)
void GRRLIB_BMFX_Sepia(const GRRLIB_texImg *src, GRRLIB_texImg *dst)
void GRRLIB_BMFX_Invert(const GRRLIB_texImg *src, GRRLIB_texImg *dst)
void GRRLIB_BMFX_Blur(const GRRLIB_texImg *src, GRRLIB_texImg *dst, const u32 factor)
void GRRLIB_BMFX_Scatter(const GRRLIB_texImg *src, GRRLIB_texImg *dst, const u32 factor)
void GRRLIB_BMFX_Pixelate(const GRRLIB_texImg *src, GRRLIB_texImg *dst, const u32 factor)
```

---

## Text / Fonts

### Bitmap font (texture-based)
```c
void GRRLIB_Printf(const f32 x, const f32 y, const GRRLIB_texImg *tex,
                   const u32 color, const f32 zoom, const char *text, ...)
```

### ByteMap font
```c
GRRLIB_bytemapFont* GRRLIB_LoadBMF(const u8 my_bmf[])
void                GRRLIB_FreeBMF(GRRLIB_bytemapFont *bmf)
void GRRLIB_PrintBMF(const f32 x, const f32 y, const GRRLIB_bytemapFont *bmf, const char *text, ...)
```

### TrueType (TTF)
```c
GRRLIB_ttfFont* GRRLIB_LoadTTF(const u8 *file_base, s32 file_size)
GRRLIB_ttfFont* GRRLIB_LoadTTFFromFile(const char *filename)
void            GRRLIB_FreeTTF(GRRLIB_ttfFont *font)

void GRRLIB_PrintfTTF(int x, int y, GRRLIB_ttfFont *font, const char *str,
                      unsigned int fontSize, const u32 color)
void GRRLIB_PrintfTTFW(int x, int y, GRRLIB_ttfFont *font, const wchar_t *str,
                       unsigned int fontSize, const u32 color)
u32  GRRLIB_WidthTTF(GRRLIB_ttfFont *font, const char *str, unsigned int fontSize)
u32  GRRLIB_WidthTTFW(GRRLIB_ttfFont *font, const wchar_t *str, unsigned int fontSize)
```

---

## Settings & Blending

```c
typedef enum { GRRLIB_BLEND_ALPHA=0, GRRLIB_BLEND_ADD=1,
               GRRLIB_BLEND_SCREEN=2, GRRLIB_BLEND_MULTI=3,
               GRRLIB_BLEND_INV=4 } GRRLIB_blendMode;
// Aliases: GRRLIB_BLEND_NONE=ALPHA, GRRLIB_BLEND_LIGHT=ADD, GRRLIB_BLEND_SHADE=MULTI

void             GRRLIB_SetBlend(const GRRLIB_blendMode mode)
GRRLIB_blendMode GRRLIB_GetBlend(void)
void             GRRLIB_SetAntiAliasing(const bool aa)
bool             GRRLIB_GetAntiAliasing(void)
void             GRRLIB_SetBackgroundColour(u8 r, u8 g, u8 b, u8 a)
```

---

## Clipping

```c
void GRRLIB_ClipDrawing(const u32 x, const u32 y, const u32 w, const u32 h)
void GRRLIB_ClipReset(void)
```

---

## Collision / Hit Testing

```c
// Point in rect
bool GRRLIB_PtInRect(const int rx, const int ry, const int rw, const int rh,
                     const int px, const int py)
// Rect fully inside another rect
bool GRRLIB_RectInRect(const int r1x, const int r1y, const int r1w, const int r1h,
                       const int r2x, const int r2y, const int r2w, const int r2h)
// Rect overlaps another rect (any corner)
bool GRRLIB_RectOnRect(const int r1x, const int r1y, const int r1w, const int r1h,
                       const int r2x, const int r2y, const int r2w, const int r2h)
```

---

## Screen Capture / Compositing

```c
void GRRLIB_Screen2Texture(u16 x, u16 y, GRRLIB_texImg *tex, bool clear) // EFB → texture (no alpha)
void GRRLIB_CompoStart(void)                                               // begin alpha composite
void GRRLIB_CompoEnd(u16 x, u16 y, GRRLIB_texImg *tex)                   // end composite → texture
bool GRRLIB_ScrShot(const char *filename)                                  // save PNG to SD card
```

---

## File I/O

```c
int GRRLIB_LoadFile(const char *filename, u8 **data) // load file → buffer; returns size
```

---

## 3D Mode

### Setup
```c
void GRRLIB_3dMode(f32 minDist, f32 maxDist, f32 fov, bool texturemode, bool normalmode)
void GRRLIB_2dMode(void)
void GRRLIB_Camera3dSettings(f32 px, f32 py, f32 pz,   // camera position
                              f32 ux, f32 uy, f32 uz,   // up vector
                              f32 lx, f32 ly, f32 lz)   // look-at point
```

### Object Transforms
```c
void GRRLIB_ObjectViewBegin(void)
void GRRLIB_ObjectViewScale(f32 sx, f32 sy, f32 sz)
void GRRLIB_ObjectViewRotate(f32 ax, f32 ay, f32 az)
void GRRLIB_ObjectViewTrans(f32 tx, f32 ty, f32 tz)
void GRRLIB_ObjectViewEnd(void)

// Combined: scale → rotate → translate
void GRRLIB_ObjectView(f32 px, f32 py, f32 pz, f32 ax, f32 ay, f32 az, f32 sx, f32 sy, f32 sz)
// Combined: scale → translate → rotate (use for camera)
void GRRLIB_ObjectViewInv(f32 px, f32 py, f32 pz, f32 ax, f32 ay, f32 az, f32 sx, f32 sy, f32 sz)

void GRRLIB_SetTexture(GRRLIB_texImg *tex, bool rep) // rep=true for repeat/wrap
```

### 3D Primitives
```c
void GRRLIB_DrawCube(f32 size, bool filled, u32 col)
void GRRLIB_DrawSphere(f32 r, int lats, int longs, bool filled, u32 col)
void GRRLIB_DrawTorus(f32 r, f32 R, int nsides, int rings, bool filled, u32 col)
void GRRLIB_DrawCylinder(f32 r, f32 h, u16 d, bool filled, u32 col)
void GRRLIB_DrawCone(f32 r, f32 h, u16 d, bool filled, u32 col)
void GRRLIB_DrawTessPanel(f32 w, f32 wstep, f32 h, f32 hstep, bool filled, u32 col)
```

### Lighting
```c
void GRRLIB_SetLightAmbient(u32 color)
void GRRLIB_SetLightDiff(u8 num, guVector pos, f32 distattn, f32 brightness, u32 color)
void GRRLIB_SetLightSpec(u8 num, guVector dir, f32 shininess, u32 lightcolor, u32 speccolor)
void GRRLIB_SetLightSpot(u8 num, guVector pos, guVector lookat,
                         f32 angAttn0, f32 angAttn1, f32 angAttn2,
                         f32 distAttn0, f32 distAttn1, f32 distAttn2, u32 color)
void GRRLIB_SetLightOff(void)
```

---

## Debug (USB Gecko)

```c
bool GRRLIB_GeckoInit(void)
void GRRLIB_GeckoPrintf(const char *text, ...)
```

---

## Minimal Game Loop

```c
#include <grrlib.h>

int main(void) {
    GRRLIB_Init();
    // load assets...

    while (1) {
        WPAD_ScanPads();
        if (WPAD_ButtonsDown(0) & WPAD_BUTTON_HOME) break;

        GRRLIB_FillScreen(0x000000FF);
        // draw calls...
        GRRLIB_Render();
    }

    GRRLIB_Exit();
    return 0;
}
```
