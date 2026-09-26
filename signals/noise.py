"""
signals/noise.py

Noise / residual analysis.

A real camera photo has fairly uniform sensor noise across the whole
frame. A spliced-in or AI-generated region often has a different,
locally-inconsistent noise signature from the rest of the image (either
too clean, or with a different residual texture). This module extracts
the high-frequency residual (image minus a denoised version of itself),
then measures how *inconsistent* that residual's statistics are across
the image, blockwise. A high inconsistency score is a hint, not proof:
some real photos are naturally noise-inconsistent too (mixed lighting,
JPEG blocking, motion blur in part of the frame).

Pipeline: original -> median-blur denoise -> residual = original - denoised
-> per-block residual std -> block-to-block inconsistency -> score.

Public entry point: analyze(image=None, image_path=None, output_dir=None)
"""

from __future__ import annotations

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

MEDIAN_KSIZE = 3       # cv2.medianBlur on a 3-channel image only accepts 3 or 5
BLOCK_GRID = 8         # 8x8 blocks for local noise-consistency statistics

# Engineering default, not scientifically calibrated (see module docstring).
INCONSISTENCY_SCALE = 1.2  # coefficient-of-variation of block stds is divided by this before clipping


def _block_stds(residual_gray: np.ndarray, grid: int) -> np.ndarray:
    h, w = residual_gray.shape
    block_h = h // grid
    block_w = w // grid

    if block_h == 0 or block_w == 0:
        # Image too small for the requested grid; fall back to a single block.
        return np.array([residual_gray.std()])

    stds = []
    for r in range(grid):
        y0, y1 = r * block_h, (r + 1) * block_h if r < grid - 1 else h
        for c in range(grid):
            x0, x1 = c * block_w, (c + 1) * block_w if c < grid - 1 else w
            block = residual_gray[y0:y1, x0:x1]
            stds.append(block.std())

    return np.array(stds)


def analyze(
    image: Optional[Union[Image.Image, np.ndarray]] = None,
    image_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Run noise/residual analysis on an image.

    Returns:
        {"name": "Noise Residual", "score": float | None, "reason": str,
         "visualization": str | None, "details": dict}
    """

    try:
        original = load_image_rgb(image, image_path)
        original_arr = np.array(original)

        denoised = cv2.medianBlur(original_arr, MEDIAN_KSIZE)

        residual = original_arr.astype(np.int16) - denoised.astype(np.int16)
        residual_gray = np.abs(residual).mean(axis=2)  # (H, W), 0..255-ish

        mean_residual = float(residual_gray.mean())
        std_residual = float(residual_gray.std())

        block_stds = _block_stds(residual_gray, BLOCK_GRID)
        block_std_mean = float(block_stds.mean())
        block_std_std = float(block_stds.std())

        # Coefficient of variation: how much the local noise level varies
        # across the image, relative to its own average level.
        noise_inconsistency = block_std_std / (block_std_mean + 1e-6)

        score = clip_score(noise_inconsistency / INCONSISTENCY_SCALE)

        # Visualization: normalized residual heatmap, colorized.
        norm = residual_gray - residual_gray.min()
        max_val = norm.max()
        if max_val > 1e-8:
            norm = norm / max_val
        residual_img = (norm * 255).astype(np.uint8)
        colored = cv2.applyColorMap(residual_img, cv2.COLORMAP_JET)

        out_dir = resolve_output_dir(output_dir, "noise")
        stem = stem_from(image_path)
        viz_path = out_dir / f"{stem}_noise.jpg"
        cv2.imwrite(str(viz_path), colored)

        reason = (
            f"Residual noise level {mean_residual:.2f}/255 on average, with a "
            f"block-to-block inconsistency (coefficient of variation) of "
            f"{noise_inconsistency:.2f} across an {BLOCK_GRID}x{BLOCK_GRID} grid. "
            f"Locally inconsistent noise can indicate a spliced or synthesized "
            f"region, but mixed lighting, motion blur, or JPEG blocking can also "
            f"cause this — not proof of manipulation on its own."
        )

        return {
            "name": "Noise Residual",
            "score": score,
            "reason": reason,
            "visualization": str(viz_path),
            "details": {
                "median_ksize": MEDIAN_KSIZE,
                "mean_residual": mean_residual,
                "std_residual": std_residual,
                "block_grid": [BLOCK_GRID, BLOCK_GRID],
                "block_std_mean": block_std_mean,
                "block_std_std": block_std_std,
                "noise_inconsistency": noise_inconsistency,
            },
        }

    except Exception as exc:  # a bad/corrupt image must not crash the pipeline
        return error_result("Noise Residual", exc)
