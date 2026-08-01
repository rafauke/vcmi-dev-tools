# VCMI Development Tools

Reusable development utilities for VCMI mod contributors. They are maintained
separately from individual mod repositories, so published mods contain only
their metadata and runtime assets.

Do not commit proprietary game data, extracted archives, credentials, local
environment files, model weights, or other material that cannot be published.

## Portrait preparation

The first utility prepares high-resolution hero portraits for portrait mods.

## Setup

Install [uv](https://docs.astral.sh/uv/), clone this repository, and run:

```bash
uv sync
```

## Build one hero

Prepare two source images:

- large portrait (`HPL`): any suitable resolution with a `29:32` aspect ratio;
- small portrait (`HPS`): any suitable resolution with a `3:2` aspect ratio.

Then point the command at the hero submod's `content` directory:

```bash
uv run vcmi-portraits build \
  --resource 003SH \
  --large /path/to/dracon_large.png \
  --small /path/to/dracon_small.png \
  --output /path/to/hd-expansion-portraits/Mods/0-armageddons-blade/Mods/03-dracon/content
```

This creates:

| Directory | HPL size | HPS size |
|---|---:|---:|
| `Data2x` | 116x128 | 96x64 |
| `Data3x` | 174x192 | 144x96 |
| `Data4x` | 232x256 | 192x128 |

Existing files with the same names are replaced. Review the generated images
and the Git diff in the target mod before committing them.

The reviewed initial roster and release grouping for this mod lives in
`manifests/hd-expansion-portraits.json`. Restoration of Erathia is conditional
on finding any uncovered campaign resources; Heroes Chronicles is deliberately
listed as future scope rather than mixed into the initial 33 resources.

## Conflux town remaster inventory

Generate a public-safe manifest from VCMI's Conflux faction configuration and
the locally installed original game archives:

```bash
uv run vcmi-conflux-inventory \
  --config /path/to/vcmi/config/factions/conflux.json \
  --data-dir /path/to/original-game/Data \
  --output manifests/conflux-town-resources.json
```

The command records referenced bitmap and DEF resources, dimensions, DEF
groups, frame order, offsets and archive availability. It does not extract or
write copyrighted image data, hashes or local filesystem paths to the manifest.

The reviewed initial vertical slice is stored in
`manifests/conflux-vertical-slice.json`. Extract its source files into an
ignored local workspace with:

```bash
uv run vcmi-conflux-extract \
  --selection manifests/conflux-vertical-slice.json \
  --data-dir /path/to/original-game/Data \
  --output /path/to/local-assets/conflux-hd/vertical-slice-original
```

The local output contains decoded PNGs and reconstruction metadata, including
source hashes and complete DEF frame offsets. Never commit that output.

With ComfyUI running, upscale the extracted flat input batch through a named
PyTorch upscale model and derive exact 2x candidates with preserved alpha:

```bash
uv run vcmi-conflux-comfy-upscale \
  --input /path/to/flat-input \
  --output /path/to/local-run \
  --model 4x_NMKD-Siax_200k.pth \
  --comfy-input /path/to/ComfyUI/input \
  --comfy-output /path/to/ComfyUI/output
```

The output directory must be new. The command records every submitted API
workflow and input/output hash for a reproducible comparison.
