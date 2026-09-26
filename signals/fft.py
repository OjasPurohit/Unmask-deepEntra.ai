"""
signals/fft.py

Frequency-domain (2D FFT) analysis.

GAN/diffusion upsampling and repeated resampling tend to leave periodic,
non-photographic structure in the frequency spectrum (visible as extra
peaks/rings in the magnitude spectrum, and an unusual amount of energy
concentrated at high spatial frequencies). This module measures that,
but a high score is a hint, not proof: strong real-world textures
(foliage, fabric, screen moire) can also produce an atypical spectrum.

Pipeline: grayscale -> resize (for a consistent frequency scale across
different input resolutions) -> 2D FFT -> fftshift -> magnitude spectrum
-> log scaling -> radial frequency statistics.

Public entry point: analyze(image=None, image_path=None, output_dir=None)
"""

from __future__ import annotations

from typing import Optional, Union

import cv2
import numpy as np
from PIL import Image
from scipy.signal import find_peaks

from signals._util import (
    clip_score,
    error_result,
    load_image_rgb,
    resolve_output_dir,
    stem_from,
)

# Grayscale is resized to this square size before FFT so radial-frequency
# statistics are comparable across images of different native resolution.
ANALYSIS_SIZE = 256

# Engineering defaults, not scientifically calibrated (see module docstring).
HIGH_FREQ_RADIUS_FRACTION = 0.75  # radius (as a fraction of max radius) where "high frequency" starts
HIGH_FREQ_RATIO_SCALE = 0.35      # high_freq_ratio is divided by this before clipping to [0,1]
PEAK_SCORE_WEIGHT = 0.05          # each detected radial peak beyond the DC region adds this much


def _radial_profile(magnitude: np.ndarray) -> np.ndarray:
    """Azimuthally-averaged magnitude as a function of radius from the center."""

    h, w = magnitude.shape
    cy, cx = h // 2, w // 2

    y, x = np.indices((h, w))
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.int32)

    max_r = r.max()
    sums = np.bincount(r.ravel(), weights=magnitude.ravel(), minlength=max_r + 1)
    counts = np.bincount(r.ravel(), minlength=max_r + 1)
    counts[counts == 0] = 1

    return sums / counts


def analyze(
    image: Optional[Union[Image.Image, np.ndarray]] = None,
    image_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Run 2D FFT frequency analysis on an image.

    Returns:
        {"name": "FFT", "score": float | None, "reason": str,
         "visualization": str | None, "details": dict}
    """

    try:
        original = load_image_rgb(image, image_path)
        gray = cv2.cvtColor(np.array(original), cv2.COLOR_RGB2GRAY)
        gray = cv2.resize(gray, (ANALYSIS_SIZE, ANALYSIS_SIZE), interpolation=cv2.INTER_AREA)

        fft = np.fft.fft2(gray.astype(np.float64))
        fft_shifted = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shifted)
        log_magnitude = np.log1p(magnitude)

        radial = _radial_profile(magnitude)
        total_energy = float(magnitude.sum())

        max_r = len(radial) - 1
        high_freq_start = int(HIGH_FREQ_RADIUS_FRACTION * max_r)
        high_freq_energy = float(radial[high_freq_start:].sum())
        # Bin 0 is the DC component (average pixel brightness), not frequency
        # content, and its magnitude is orders of magnitude larger than any
        # AC bin (e.g. ~75% of this profile's total sum on a sample real
        # photo) -- including it here was a bug: it swamped low_freq_energy
        # and collapsed high_freq_ratio toward ~0 for every image regardless
        # of actual texture/content. Excluded, as is standard practice.
        low_freq_energy = float(radial[1:high_freq_start].sum())
        high_freq_ratio = high_freq_energy / (high_freq_energy + low_freq_energy + 1e-8)

        # Peaks in the (log-scaled, DC-excluded) radial profile: periodic
        # upsampling artifacts show up as distinct bumps rather than the
        # smooth monotonic falloff typical of natural-photo spectra.
        radial_log = np.log1p(radial[5:])  # skip the first few bins (DC + immediate neighborhood)
        if radial_log.size > 3:
            peak_indices, _ = find_peaks(radial_log, prominence=radial_log.std() * 0.5 + 1e-6)
            peak_count = int(len(peak_indices))
        else:
            peak_count = 0

        score = clip_score(high_freq_ratio / HIGH_FREQ_RATIO_SCALE + PEAK_SCORE_WEIGHT * peak_count)

        # Visualization: normalized log-magnitude spectrum, colorized.
        norm = log_magnitude - log_magnitude.min()
        max_val = norm.max()
        if max_val > 1e-8:
            norm = norm / max_val
        spectrum_img = (norm * 255).astype(np.uint8)
        colored = cv2.applyColorMap(spectrum_img, cv2.COLORMAP_INFERNO)

        out_dir = resolve_output_dir(output_dir, "fft")
        stem = stem_from(image_path)
        viz_path = out_dir / f"{stem}_fft.jpg"
        cv2.imwrite(str(viz_path), colored)

        reason = (
            f"High-frequency energy ratio {high_freq_ratio * 100:.1f}% "
            f"(radius >= {HIGH_FREQ_RADIUS_FRACTION * 100:.0f}% of max) with "
            f"{peak_count} radial spectrum peak(s) detected. Elevated high-frequency "
            f"energy and periodic peaks can indicate GAN/diffusion upsampling "
            f"artifacts, but strong natural textures can also produce this — "
            f"not proof of manipulation on its own."
        )

        return {
            "name": "FFT",
            "score": score,
            "reason": reason,
            "visualization": str(viz_path),
            "details": {
                "analysis_size": [ANALYSIS_SIZE, ANALYSIS_SIZE],
                "total_energy": total_energy,
                "high_freq_energy": high_freq_energy,
                "low_freq_energy": low_freq_energy,
                "high_freq_ratio": high_freq_ratio,
                "peak_count": peak_count,
                "radial_profile_length": int(len(radial)),
            },
        }

    except Exception as exc:  # a bad/corrupt image must not crash the pipeline
        return error_result("FFT", exc)
