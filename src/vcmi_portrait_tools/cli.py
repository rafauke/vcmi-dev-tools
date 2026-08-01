"""Command-line tools for producing VCMI HD portrait assets."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image


SIZES = {
    "Data2x": {"HPL": (116, 128), "HPS": (96, 64)},
    "Data3x": {"HPL": (174, 192), "HPS": (144, 96)},
    "Data4x": {"HPL": (232, 256), "HPS": (192, 128)},
}
ASPECTS = {"HPL": 29 / 32, "HPS": 3 / 2}
RESOURCE_PATTERN = re.compile(r"^[A-Z0-9]{5}$")


def normalized_resource(value: str) -> str:
    resource = value.upper()
    if not RESOURCE_PATTERN.fullmatch(resource):
        raise argparse.ArgumentTypeError(
            "resource must contain exactly five ASCII letters or digits, e.g. 003SH"
        )
    return resource


def validate_master(path: Path, kind: str) -> None:
    if not path.is_file():
        raise ValueError(f"source image does not exist: {path}")
    with Image.open(path) as image:
        actual = image.width / image.height
    if abs(actual - ASPECTS[kind]) > 0.002:
        raise ValueError(
            f"{path} has aspect ratio {actual:.6f}; "
            f"expected {ASPECTS[kind]:.6f} for {kind}"
        )


def build_portrait(master: Path, kind: str, resource: str, output: Path) -> None:
    validate_master(master, kind)
    with Image.open(master) as image:
        for data_dir, dimensions in SIZES.items():
            size = dimensions[kind]
            destination = output / data_dir / f"{kind}{resource}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.resize(size, Image.Resampling.LANCZOS).save(
                destination, format="PNG", optimize=True
            )
            print(f"created {destination} ({size[0]}x{size[1]})")


def build(args: argparse.Namespace) -> None:
    try:
        validate_master(args.large, "HPL")
        validate_master(args.small, "HPS")
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error

    build_portrait(args.large, "HPL", args.resource, args.output)
    build_portrait(args.small, "HPS", args.resource, args.output)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="vcmi-portraits")
    commands = root.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser(
        "build", help="create Data2x, Data3x and Data4x portrait assets"
    )
    build_command.add_argument(
        "--resource", required=True, type=normalized_resource,
        help="five-character VCMI portrait suffix, e.g. 003SH",
    )
    build_command.add_argument("--large", required=True, type=Path)
    build_command.add_argument("--small", required=True, type=Path)
    build_command.add_argument(
        "--output", required=True, type=Path,
        help="target hero submod's content directory",
    )
    build_command.set_defaults(handler=build)
    return root


def main() -> None:
    args = parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()

