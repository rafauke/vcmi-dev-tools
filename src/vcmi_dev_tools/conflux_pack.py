"""Pack upscaled Conflux DEF frames as VCMI-compatible D32 resources."""

from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path
import struct
from typing import Any

from homm3data import deffile
import numpy as np
from PIL import Image


D32_MAGIC = 0x46323344


def encode_frame(image: Image.Image) -> bytes:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    bgra = rgba[:, :, [2, 1, 0, 3]]
    return np.ascontiguousarray(np.flipud(bgra)).tobytes()


def write_d32(groups: dict[int, list[tuple[str, Image.Image]]], output: Path) -> None:
    if not groups or any(not frames for frames in groups.values()):
        raise ValueError("D32 requires at least one frame in every group")
    dimensions = {
        image.size for frames in groups.values() for _, image in frames
    }
    if len(dimensions) != 1:
        raise ValueError(f"all D32 frames must share one canvas size: {dimensions}")
    width, height = dimensions.pop()

    header_size = 32 + sum(16 + 17 * len(frames) for frames in groups.values())
    encoded: list[tuple[int, int, str, bytes]] = []
    offset = header_size
    for group, frames in sorted(groups.items()):
        for index, (name, image) in enumerate(frames):
            pixels = encode_frame(image)
            encoded.append((group, index, name, pixels))
            offset += 40 + len(pixels)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        stream.write(struct.pack("<8I", D32_MAGIC, 1, 24, width, height, len(groups), 8, 0))
        offset = header_size
        by_group: dict[int, list[tuple[int, int, str, bytes]]] = {}
        for item in encoded:
            by_group.setdefault(item[0], []).append(item)
        for group, frames in sorted(by_group.items()):
            stream.write(struct.pack("<4I", 16 + 17 * len(frames), group, len(frames), 4))
            for _, _, name, _ in frames:
                raw_name = name.encode("cp1252", errors="replace")[:12]
                stream.write(struct.pack("<13s", raw_name))
            for _, _, _, pixels in frames:
                stream.write(struct.pack("<I", offset))
                offset += 40 + len(pixels)
        for _, _, _, pixels in encoded:
            stream.write(
                struct.pack(
                    "<10I",
                    32,
                    len(pixels),
                    width,
                    height,
                    width,
                    height,
                    0,
                    0,
                    8,
                    1,
                )
            )
            stream.write(pixels)


def load_groups(
    resource: dict[str, Any], extracted_root: Path, upscaled_root: Path
) -> dict[int, list[tuple[str, Image.Image]]]:
    groups: dict[int, list[tuple[str, Image.Image]]] = {}
    for frame in resource["details"]["frames"]:
        source_file = extracted_root / resource["output"] / frame["file"]
        upscaled_file = upscaled_root / source_file.name
        if not upscaled_file.is_file():
            raise FileNotFoundError(upscaled_file)
        with Image.open(upscaled_file) as image:
            groups.setdefault(frame["group"], []).append(
                (frame["sourceName"], image.convert("RGBA"))
            )
    return groups


def validate_d32(path: Path, expected_groups: dict[int, list[tuple[str, Image.Image]]]) -> None:
    with deffile.open(BytesIO(path.read_bytes())) as archive:
        expected_size = next(iter(expected_groups.values()))[0][1].size
        if archive.get_size() != expected_size:
            raise ValueError(f"D32 canvas mismatch: {path}")
        if archive.get_groups() != sorted(expected_groups):
            raise ValueError(f"D32 group mismatch: {path}")
        for group, frames in expected_groups.items():
            if archive.get_frame_count(group) != len(frames):
                raise ValueError(f"D32 frame-count mismatch: {path}, group {group}")
            for index, (_, expected) in enumerate(frames):
                decoded = archive.read_image(group_id=group, image_id=index)
                if decoded is None or decoded.tobytes() != expected.tobytes():
                    raise ValueError(f"D32 pixel mismatch: {path}, frame {group}:{index}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--upscaled", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    document = json.loads(args.metadata.read_text(encoding="utf-8"))
    extracted_root = args.metadata.parent
    packed = 0
    for resource in document["resources"]:
        if resource["kind"] != "def":
            continue
        groups = load_groups(resource, extracted_root, args.upscaled)
        output = args.output / resource["runtimeName"]
        write_d32(groups, output)
        validate_d32(output, groups)
        packed += 1
        print(f"packed and validated {output}")
    print(f"packed {packed} D32 resources")


if __name__ == "__main__":
    main()
