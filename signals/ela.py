"""
signals/ela.py

Error Level Analysis (ELA).

Idea: re-save the image as JPEG at a fixed quality, then diff it against
the original. Regions that were edited/pasted-in after the original JPEG
generation, or that were generated rather than photographed, tend to
recompress differently (higher or lower local error) than the rest of a
naturally-uniform photograph. A high ELA response is a hint, not proof:
plenty of ordinary edits (crops, resaves, watermarks) also raise it, so
this is supporting forensic evidence only.

Public entry point: analyze(image=None, image_path=None, output_dir=None, quality=90)
"""

from __future__ import annotations

import io
from typing import Optional, Union

import cv2
import numpy as np
from PIL import Image

from signals._util import (
    clip_score,
    error_result,
    load_image_rgb,
    resolve_output_dir,
    stem_from,
)

# Engineering default, not scientifically calibrated. Chosen so that
# ordinary photos (mean ELA response of a few grey levels) land in the
# low range and heavily re-edited/synthetic images land higher. This will
# be recalibrated against real data during the evidence-fusion stage.
DEFAULT_QUALITY = 90
SCORE_SCALE = 25.0  # mean_diff (0..255) is divided by this before clipping to [0,1]


def _recompress(image_rgb: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image_rgb.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def analyze(
    image: Optional[Union[Image.Image, np.ndarray]] = None,
    image_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    quality: int = DEFAULT_QUALITY,
) -> dict:
    """
    Run Error Level Analysis on an image.

    Returns:
        {"name": "ELA", "score": float | None, "reason": str,
         "visualization": str | None, "details": dict}
    """

    try:
        original = load_image_rgb(image, image_path)
        original_arr = np.array(original).astype(np.int16)

        recompressed = _recompress(original, quality)
        recompressed_arr = np.array(recompressed).astype(np.int16)

        if original_arr.shape != recompressed_arr.shape:
            # Recompression should never change dimensions, but guard anyway.
            recompressed_arr = cv2.resize(
                recompressed_arr.astype(np.uint8),
                (original_arr.shape[1], original_arr.shape[0]),
            ).astype(np.int16)

        diff = np.abs(original_arr - recompressed_arr)  # (H, W, 3), 0..255
        diff_gray = diff.mean(axis=2)  # (H, W)

        mean_diff = float(diff_gray.mean())
        max_diff = float(diff_gray.max())
        std_diff = float(diff_gray.std())

        score = clip_score(mean_diff / SCORE_SCALE)

        # Amplified visualization: scale so the typical response is visible,
        # then apply a colormap for a more legible frontend-ready image.
        amplified = np.clip(diff_gray * 15, 0, 255).astype(np.uint8)
        colored = cv2.applyColorMap(amplified, cv2.COLORMAP_JET)

        out_dir = resolve_output_dir(output_dir, "ela")
        stem = stem_from(image_path)
        viz_path = out_dir / f"{stem}_ela.jpg"
        cv2.imwrite(str(viz_path), colored)

        reason = (
            f"Mean error-level intensity {mean_diff:.2f}/255 after JPEG q={quality} "
            f"recompression (max {max_diff:.1f}, std {std_diff:.2f}). Elevated, "
            f"spatially concentrated error levels can indicate localized editing "
            f"or re-encoding, but ordinary edits and resaves also raise this value "
            f"— not proof of manipulation on its own."
        )

        return {
            "name": "ELA",
            "score": score,
            "reason": reason,
            "visualization": str(viz_path),
            "details": {
                "quality": quality,
                "mean_diff": mean_diff,
                "max_diff": max_diff,
                "std_diff": std_diff,
                "image_size": [original.width, original.height],
            },
        }

    except Exception as exc:  # a bad/corrupt image must not crash the pipeline
        return error_result("ELA", exc)
