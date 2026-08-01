"""Export upscaled Conflux frames with names used by VCMI's HD loader."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from PIL import Image


def frame_output_name(source_name: str) -> str:
    return f"{Path(source_name).stem}.png"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--upscaled", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    document = json.loads(args.metadata.read_text(encoding="utf-8"))
    extracted_root = args.metadata.parent
    outputs: dict[str, tuple[str, Path]] = {}
    for resource in document["resources"]:
        if resource["kind"] != "def":
            continue
        for frame in resource["details"]["frames"]:
            extracted = extracted_root / resource["output"] / frame["file"]
            upscaled = args.upscaled / extracted.name
            if not upscaled.is_file():
                raise FileNotFoundError(upscaled)
            output_name = frame_output_name(frame["sourceName"])
            key = output_name.casefold()
            if key in outputs:
                raise ValueError(
                    f"duplicate HD frame output {output_name}: "
                    f"{outputs[key][1]} and {upscaled}"
                )
            outputs[key] = (output_name, upscaled)

    args.output.mkdir(parents=True, exist_ok=True)
    for _, (output_name, source) in sorted(outputs.items()):
        destination = args.output / output_name
        shutil.copy2(source, destination)
        with Image.open(source) as expected, Image.open(destination) as actual:
            if expected.size != actual.size or expected.tobytes() != actual.tobytes():
                raise ValueError(f"export validation failed: {destination}")
        print(f"exported {destination}")
    print(f"exported {len(outputs)} HD sprite frames")


if __name__ == "__main__":
    main()
