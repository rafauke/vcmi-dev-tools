# VCMI HD resource override findings

Verified against VCMI 1.7.4 (`9949b089`) and its runtime trace log.

## Bitmap resources

For a bitmap reference such as `TBELBACK.bmp`, place a scaled PNG with the
resource stem in the matching scale directory:

```text
content/Data2x/TBELBACK.png
content/Data3x/TBELBACK.png
content/Data4x/TBELBACK.png
```

VCMI resolves these loose PNGs before the HD Edition bitmap PAK. Palette-index
transparency in original PCX resources must be converted to explicit PNG alpha.

## DEF animation resources

Do not replace the original DEF with a high-resolution DEF or D32 file. VCMI
uses the original DEF as an animation manifest: it reads groups, frame order,
canvas dimensions, offsets and each frame's internal filename. For every frame,
it removes the extension and asks the HD image loader for an image with that
name.

For example, `TBELTVRN.def` contains the frame `TBELtvrn.pcx`. The correct HD
override is therefore:

```text
content/Data2x/TBELtvrn.png
content/Data3x/TBELtvrn.png
content/Data4x/TBELtvrn.png
```

The scaled PNG must retain the complete scaled DEF canvas and the frame content
at its scaled original offset. This lets the low-resolution DEF metadata remain
authoritative while VCMI substitutes the loose high-resolution frame.

The same rule applies to multi-frame and multi-group animations: export every
internal frame name as one PNG. Detect case-insensitive filename collisions
before writing anything.

## Runtime verification

Enable trace logging and inspect `VCMI_Client_log.txt`. A successful loose
override includes a line loading the PNG from the mod's `content/DataNx`
directory. Repeated loads from `hd-edition/.../sprite_DXT_com_xN.pak` without a
corresponding mod PNG show that VCMI did not find the loose frame override.

Relevant VCMI 1.7.4 implementation files are:

- `client/renderSDL/RenderHandler.cpp`, especially `getAnimationFrameName`;
- `client/render/CDefFile.cpp`, which reads the original DEF metadata;
- `client/render/hdEdition/HdImageLoader.cpp`, which resolves scaled HD frames.

