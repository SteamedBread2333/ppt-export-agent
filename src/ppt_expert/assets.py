from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from ppt_expert.models import DesignSpec, ImageRequest
from ppt_expert.runtime import HostRuntime

LOGGER = logging.getLogger(__name__)


async def generate_assets(
    runtime: HostRuntime,
    requests: list[ImageRequest],
    design: DesignSpec,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}
    for request in requests:
        digest = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:12]
        output_path = output_dir / f"{request.image_id}_{digest}.png"
        if output_path.exists():
            results[request.image_id] = str(output_path.resolve())
            continue
        try:
            generated = await runtime.generate_image(request, output_path)
        except Exception as exc:  # noqa: BLE001 - host tools can raise provider-specific errors
            LOGGER.warning("Host image generation failed for %s: %s", request.image_id, exc)
            generated = None
        if generated is None or not generated.exists():
            _placeholder(output_path, request, design)
            generated = output_path.resolve()
        results[request.image_id] = str(generated)
    return results


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
