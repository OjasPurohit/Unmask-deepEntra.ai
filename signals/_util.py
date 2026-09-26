"""
signals/_util.py

Small shared helpers so signals/ela.py, fft.py, noise.py and metadata.py
don't each reimplement image loading, output-path handling and the
common failure-result shape. Not itself a signal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_image_rgb(
    image: Optional[Union[Image.Image, np.ndarray]] = None,
    image_path: Optional[Union[str, Path]] = None,
) -> Image.Image:
    """
    Resolve `image` and/or `image_path` into a single RGB PIL.Image.

    - If `image` is given (PIL.Image or RGB ndarray), it is used directly.
    - Otherwise `image_path` is opened.
    - If neither is given, raises ValueError.
    """

    if image is not None:
        if isinstance(image, Image.Image):
            return image.convert("RGB")
        if isinstance(image, np.ndarray):
            return Image.fromarray(image.astype(np.uint8)).convert("RGB")
        raise TypeError(f"image must be a PIL.Image or numpy array, got {type(image)}")

    if image_path is not None:
        return Image.open(image_path).convert("RGB")

    raise ValueError("Either `image` or `image_path` must be provided.")


def resolve_output_dir(output_dir: Optional[Union[str, Path]], default_subdir: str) -> Path:
    """Pick the output directory: `output_dir` if given, else test_data/forensic/<default_subdir>/."""

    out_dir = Path(output_dir) if output_dir is not None else PROJECT_ROOT / "test_data" / "forensic" / default_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def stem_from(image_path: Optional[Union[str, Path]], fallback: str = "image") -> str:
    return Path(image_path).stem if image_path is not None else fallback


def clip_score(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def error_result(name: str, exc: Exception) -> dict:
    """
    The standard shape for a signal that could not be calculated. Score is
    explicitly None (never a fabricated number) and the real exception is
    surfaced in details.error, not swallowed.
    """

    return {
        "name": name,
        "score": None,
        "reason": "Unable to calculate signal.",
        "visualization": None,
        "details": {"error": f"{type(exc).__name__}: {exc}"},
    }
