"""Extract selected Conflux resources into a local PNG work directory."""

from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Any

from homm3data import deffile, pcxfile

from vcmi_dev_tools.conflux_inventory import open_archives


SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def load_selection(path: Path) -> list[dict[str, str]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    resources = document.get("resources")
    if not isinstance(resources, list) or not resources:
        raise ValueError("selection manifest must contain a non-empty resources list")

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in resources:
        if not isinstance(item, dict):
            raise ValueError("each selected resource must be an object")
        entry = item.get("archiveEntry")
        runtime_name = item.get("runtimeName")
        role = item.get("role")
        if not all(isinstance(value, str) and value for value in (entry, runtime_name, role)):
            raise ValueError("each resource requires archiveEntry, runtimeName and role")
        entry = entry.casefold()
        if not entry.endswith((".pcx", ".def")):
            raise ValueError(f"unsupported selected resource: {entry}")
        if entry in seen:
            raise ValueError(f"duplicate selected resource: {entry}")
        seen.add(entry)
        result.append({"archiveEntry": entry, "runtimeName": runtime_name, "role": role})
    return result


def safe_stem(value: str) -> str:
    return SAFE_NAME.sub("_", Path(value).stem)


def extract_bitmap(data: bytes, destination: Path) -> dict[str, Any]:
    image = pcxfile.read_pcx(data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return {"width": image.width, "height": image.height, "mode": image.mode}


def extract_def(data: bytes, destination: Path) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    with deffile.open(BytesIO(data)) as archive:
        width, height = archive.get_size()
        for item in archive.get_raw_data():
            group = item["group_id"]
            index = item["image_id"]
            source_name = item["name"]
            frame_path = (
                destination
                / f"group-{group:03d}"
                / f"frame-{index:03d}-{safe_stem(source_name)}.png"
            )
            frame_path.parent.mkdir(parents=True, exist_ok=True)
            image = archive.read_image(group_id=group, image_id=index)
            if image is None:
                raise ValueError(f"could not decode DEF frame {group}:{index}")
            image.save(frame_path)
            raw_image = item["image"]
            frames.append(
                {
                    "group": group,
                    "index": index,
                    "sourceName": source_name,
                    "file": frame_path.relative_to(destination).as_posix(),
                    "fullWidth": raw_image["full_width"],
                    "fullHeight": raw_image["full_height"],
                    "storedWidth": raw_image["width"],
                    "storedHeight": raw_image["height"],
                    "marginLeft": raw_image["margin_left"],
                    "marginTop": raw_image["margin_top"],
                    "compression": raw_image["format"],
                }
            )
        return {
            "defType": archive.get_type().name,
            "width": width,
            "height": height,
            "groups": archive.get_groups(),
            "frames": frames,
        }


def extract(selection_path: Path, data_dir: Path, output: Path) -> dict[str, Any]:
    selection = load_selection(selection_path)
    contents, locations = open_archives(data_dir)
    missing = [item["archiveEntry"] for item in selection if item["archiveEntry"] not in contents]
    if missing:
        raise FileNotFoundError(f"missing selected resources: {', '.join(missing)}")

    output.mkdir(parents=True, exist_ok=True)
    extracted: list[dict[str, Any]] = []
    for item in selection:
        entry = item["archiveEntry"]
        data = contents[entry]
        if entry.endswith(".pcx"):
            relative_output = Path("bitmaps") / f"{safe_stem(item['runtimeName'])}.png"
            details = extract_bitmap(data, output / relative_output)
            kind = "bitmap"
        else:
            relative_output = Path("defs") / safe_stem(item["runtimeName"])
            details = extract_def(data, output / relative_output)
            kind = "def"
        extracted.append(
            {
                **item,
                "kind": kind,
                "availableIn": locations[entry],
                "sourceSha256": sha256(data).hexdigest(),
                "output": relative_output.as_posix(),
                "details": details,
            }
        )

    metadata = {"schemaVersion": 1, "resources": extracted}
    (output / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return metadata


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--selection", required=True, type=Path)
    result.add_argument("--data-dir", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def main() -> None:
    args = parser().parse_args()
    metadata = extract(args.selection, args.data_dir, args.output)
    frame_count = sum(
        len(item["details"].get("frames", [])) for item in metadata["resources"]
    )
    print(f"wrote {args.output}")
    print(f"resources: {len(metadata['resources'])}, DEF frames: {frame_count}")


if __name__ == "__main__":
    main()
