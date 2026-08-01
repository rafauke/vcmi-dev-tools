"""Run a reproducible Conflux upscale batch through the local ComfyUI API."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import time
import urllib.request
import uuid

from PIL import Image


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def workflow(image: str, model: str, prefix: str) -> dict:
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image}},
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": model},
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"image": ["1", 0], "upscale_model": ["2", 0]},
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {"images": ["3", 0], "filename_prefix": prefix},
        },
    }


def wait_for_result(base_url: str, prompt_id: str) -> dict:
    while True:
        history = request_json(f"{base_url}/history/{prompt_id}")
        if prompt_id in history:
            result = history[prompt_id]
            status = result.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(json.dumps(status, indent=2))
            if status.get("completed"):
                return result
        time.sleep(1)


def restore_alpha(source: Image.Image, image: Image.Image) -> Image.Image:
    if source.mode != "RGBA":
        return image.convert("RGB")
    alpha = source.getchannel("A").resize(image.size, Image.Resampling.LANCZOS)
    bbox = source.getchannel("A").getbbox()
    if bbox:
        scale_x = image.width // source.width
        scale_y = image.height // source.height
        scaled = (
            bbox[0] * scale_x,
            bbox[1] * scale_y,
            bbox[2] * scale_x,
            bbox[3] * scale_y,
        )
        clipped = Image.new("L", image.size, 0)
        clipped.paste(alpha.crop(scaled), scaled)
        alpha = clipped
    result = image.convert("RGBA")
    result.putalpha(alpha)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="4x_NMKD-Siax_200k.pth")
    parser.add_argument("--url", default="http://127.0.0.1:8188")
    parser.add_argument("--comfy-input", required=True, type=Path)
    parser.add_argument("--comfy-output", required=True, type=Path)
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    sources = sorted(args.input.glob("*.png"))
    if not sources:
        raise SystemExit(f"no PNG inputs found: {args.input}")

    available = request_json(f"{args.url}/object_info/UpscaleModelLoader")
    options = available["UpscaleModelLoader"]["input"]["required"]["model_name"][1]["options"]
    if args.model not in options:
        raise SystemExit(f"ComfyUI does not expose model {args.model}")

    run_id = f"conflux-{args.output.name}-{uuid.uuid4().hex[:8]}"
    staged = args.comfy_input / run_id
    staged.mkdir(parents=True)
    for folder in ("workflows", "x4", "x2"):
        (args.output / folder).mkdir(parents=True)

    records = []
    client_id = str(uuid.uuid4())
    for source_path in sources:
        staged_path = staged / source_path.name
        shutil.copy2(source_path, staged_path)
        prefix = f"{run_id}/{source_path.stem}"
        graph = workflow(f"{run_id}/{source_path.name}", args.model, prefix)
        (args.output / "workflows" / f"{source_path.stem}.api.json").write_text(
            json.dumps(graph, indent=2) + "\n", encoding="utf-8"
        )
        queued = request_json(
            f"{args.url}/prompt", {"prompt": graph, "client_id": client_id}
        )
        result = wait_for_result(args.url, queued["prompt_id"])
        image_info = result["outputs"]["4"]["images"][0]
        generated = (
            args.comfy_output / image_info["subfolder"] / image_info["filename"]
        )
        with Image.open(source_path) as source, Image.open(generated) as raw_x4:
            source.load()
            raw_x4.load()
            x4 = restore_alpha(source, raw_x4)
            x4_path = args.output / "x4" / source_path.name
            x4.save(x4_path)
            x2_raw = x4.resize(
                (source.width * 2, source.height * 2), Image.Resampling.LANCZOS
            )
            x2 = restore_alpha(source, x2_raw)
            x2_path = args.output / "x2" / source_path.name
            x2.save(x2_path)
        records.append(
            {
                "file": source_path.name,
                "sourceSha256": digest(source_path),
                "x4Sha256": digest(x4_path),
                "x2Sha256": digest(x2_path),
                "workflow": f"workflows/{source_path.stem}.api.json",
            }
        )
        print(f"completed {source_path.name}", flush=True)

    metadata = {
        "schemaVersion": 1,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "backend": "ComfyUI local API",
        "model": args.model,
        "targetScale": 2,
        "masterScale": 4,
        "alpha": "source alpha scaled and clipped to scaled source bounds",
        "resources": records,
    }
    (args.output / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
