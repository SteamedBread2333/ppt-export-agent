from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from ppt_expert.models import DesignSpec, ImageRequest
from ppt_expert.runtime import HostRuntime

LOGGER = logging.getLogger(__name__)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


async def generate_assets(
    runtime: HostRuntime,
    requests: list[ImageRequest],
    design: DesignSpec,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not requests:
        return {}
    completed = await asyncio.gather(
        *[_materialize(runtime, request, design, output_dir) for request in requests]
    )
    return dict(completed)


async def _materialize(
    runtime: HostRuntime,
    request: ImageRequest,
    design: DesignSpec,
    output_dir: Path,
) -> tuple[str, str]:
    digest = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:12]
    output_path = output_dir / f"{request.image_id}_{digest}.png"
    if output_path.exists():
        try:
            normalized = _normalize_to_png(output_path, output_path)
        except OSError as exc:
            LOGGER.warning("Cached image is invalid for %s: %s", request.image_id, exc)
            _placeholder(output_path, request, design)
            normalized = output_path.resolve()
        return request.image_id, str(normalized)
    try:
        generated = await runtime.generate_image(request, output_path)
    except Exception as exc:  # noqa: BLE001 - host tools can raise provider-specific errors
        LOGGER.warning("Host image generation failed for %s: %s", request.image_id, exc)
        generated = None
    candidate = _generated_candidate(generated, output_path)
    if candidate is not None:
        try:
            generated = _normalize_to_png(candidate, output_path)
        except OSError as exc:
            LOGGER.warning("Generated image conversion failed for %s: %s", request.image_id, exc)
            generated = None
    if generated is None:
        _placeholder(output_path, request, design)
        generated = output_path.resolve()
    return request.image_id, str(generated)


def _generated_candidate(generated: Path | None, output_path: Path) -> Path | None:
    if generated is not None and generated.is_file():
        return generated
    if output_path.is_file():
        return output_path
    matches = sorted(
        path
        for path in output_path.parent.iterdir()
        if path.is_file()
        and path.stem == output_path.stem
        and path.suffix.lower() in IMAGE_SUFFIXES
    )
    return matches[0] if matches else None


def _normalize_to_png(source: Path, output_path: Path) -> Path:
    source = source.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    with Image.open(source) as image:
        image.load()
        if image.format == "PNG" and source == output_path:
            return output_path
        has_alpha = image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        )
        normalized = image.convert("RGBA" if has_alpha else "RGB")
        temporary = output_path.with_name(f".{output_path.stem}.converting.png")
        normalized.save(temporary, format="PNG")
    temporary.replace(output_path)
    return output_path


def _placeholder(path: Path, request: ImageRequest, design: DesignSpec) -> None:
    image = Image.new("RGB", (request.width, request.height), design.background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, request.width * 0.42, request.height), fill=design.primary)
    draw.ellipse(
        (
            request.width * 0.12,
            request.height * 0.18,
            request.width * 0.52,
            request.height * 0.78,
        ),
        fill=design.secondary,
    )
    draw.ellipse(
        (
            request.width * 0.04,
            request.height * 0.58,
            request.width * 0.25,
            request.height * 0.9,
        ),
        fill=design.accent,
    )
    image.save(path)
