"""Inventory Conflux town-screen resources from VCMI config and H3 LODs."""

from __future__ import annotations

import argparse
from collections import defaultdict
from io import BytesIO
import json
from pathlib import Path
from typing import Any

from homm3data import deffile, lodfile, pcxfile


STRUCTURE_RESOURCE_FIELDS = ("animation", "area", "border", "campaignBonus")
TOWN_RESOURCE_FIELDS = (
    "buildingsIcons",
    "guildBackground",
    "guildWindow",
    "hallBackground",
    "townBackground",
)
DEFAULT_ARCHIVES = (
    "H3bitmap.lod",
    "H3sprite.lod",
    "H3ab_bmp.lod",
    "H3ab_spr.lod",
)


def resource_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def archive_name(resource: str) -> str:
    path = Path(resource)
    suffix = path.suffix.casefold()
    if suffix == ".bmp":
        return f"{path.stem}.pcx".casefold()
    return path.name.casefold()


def collect_references(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    try:
        town = config["conflux"]["town"]
    except (KeyError, TypeError) as error:
        raise ValueError("config must contain conflux.town") from error

    references: dict[str, dict[str, Any]] = {}

    def add(resource: str, role: str, structure: str | None = None) -> None:
        key = archive_name(resource)
        entry = references.setdefault(
            key,
            {
                "resource": Path(resource).name,
                "archiveEntry": key,
                "roles": [],
                "structures": [],
            },
        )
        if role not in entry["roles"]:
            entry["roles"].append(role)
        if structure is not None and structure not in entry["structures"]:
            entry["structures"].append(structure)

    for field in TOWN_RESOURCE_FIELDS:
        for resource in resource_values(town.get(field)):
            add(resource, field)

    structures = town.get("structures", {})
    if not isinstance(structures, dict):
        raise ValueError("conflux.town.structures must be an object")
    for structure_name, structure in structures.items():
        if not isinstance(structure, dict):
            continue
        for field in STRUCTURE_RESOURCE_FIELDS:
            for resource in resource_values(structure.get(field)):
                add(resource, field, structure_name)

    for entry in references.values():
        entry["roles"].sort()
        entry["structures"].sort()
    return references


def open_archives(data_dir: Path) -> tuple[dict[str, bytes], dict[str, list[str]]]:
    contents: dict[str, bytes] = {}
    locations: dict[str, list[str]] = defaultdict(list)
    for filename in DEFAULT_ARCHIVES:
        path = data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"missing required archive: {path}")
        with lodfile.open(str(path)) as archive:
            for entry in archive.get_filelist():
                locations[entry].append(filename)
                if entry not in contents:
                    data = archive.get_file(entry)
                    if data is not None:
                        contents[entry] = data
    return contents, locations


def inspect_pcx(data: bytes) -> dict[str, Any]:
    if not pcxfile.is_pcx(data):
        raise ValueError("archive entry is not a Heroes III PCX")
    image = pcxfile.read_pcx(data)
    return {
        "kind": "bitmap",
        "source": {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
        },
    }


def inspect_def(data: bytes) -> dict[str, Any]:
    with deffile.open(BytesIO(data)) as archive:
        raw = archive.get_raw_data()
        frames = []
        for item in raw:
            image = item.get("image") or {}
            frames.append(
                {
                    "group": item["group_id"],
                    "index": item["image_id"],
                    "name": item["name"],
                    "fullWidth": image.get("full_width"),
                    "fullHeight": image.get("full_height"),
                    "storedWidth": image.get("width"),
                    "storedHeight": image.get("height"),
                    "marginLeft": image.get("margin_left"),
                    "marginTop": image.get("margin_top"),
                    "compression": image.get("format"),
                }
            )
        groups = [
            {"id": group, "frameCount": archive.get_frame_count(group)}
            for group in archive.get_groups()
        ]
        width, height = archive.get_size()
        return {
            "kind": "def",
            "source": {
                "width": width,
                "height": height,
                "defType": archive.get_type().name,
                "groupCount": len(groups),
                "frameCount": len(frames),
                "groups": groups,
                "frames": frames,
            },
        }


def build_manifest(config_path: Path, data_dir: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    references = collect_references(config)
    contents, locations = open_archives(data_dir)
    missing = sorted(set(references) - set(contents))
    if missing:
        raise FileNotFoundError(f"missing referenced resources: {', '.join(missing)}")

    resources = []
    for key, reference in sorted(references.items()):
        if key.endswith(".pcx"):
            details = inspect_pcx(contents[key])
        elif key.endswith(".def"):
            details = inspect_def(contents[key])
        else:
            raise ValueError(f"unsupported resource type: {key}")
        resources.append(
            {
                **reference,
                **details,
                "availableIn": locations[key],
                "targets": ["Data2x", "Data3x", "Data4x"],
                "processingProfile": "unassigned",
                "status": "pending",
                "manualReview": False,
                "verifiedInGame": False,
            }
        )

    return {
        "schemaVersion": 1,
        "project": "conflux-hd-remaster",
        "scope": "Conflux town screen",
        "sourceConfig": "VCMI config/factions/conflux.json",
        "resourceCount": len(resources),
        "resources": resources,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", required=True, type=Path)
    result.add_argument("--data-dir", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def main() -> None:
    args = parser().parse_args()
    manifest = build_manifest(args.config, args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    kinds = defaultdict(int)
    for resource in manifest["resources"]:
        kinds[resource["kind"]] += 1
    print(f"wrote {args.output}")
    print(f"resources: {manifest['resourceCount']}")
    print("kinds: " + ", ".join(f"{key}={value}" for key, value in sorted(kinds.items())))


if __name__ == "__main__":
    main()

