"""S1: cf (CommunityForensics, full image) + probe (face-crop embedding). OWNER: Omkar. STUB."""
from pathlib import Path

import numpy as np

from backend.schemas import RegionScore, Signal

REGIONS = ["jaw_boundary", "mouth", "left_eye", "right_eye", "nose", "skin", "background"]


def predict_batch(imgs: list[np.ndarray]) -> list[float]:
    return [0.5 for _ in imgs]


def region_scores(heat: np.ndarray | None, masks: dict) -> list[RegionScore]:
    vals = [0.81, 0.55, 0.38, 0.35, 0.30, 0.27, 0.12]
    return [RegionScore(region=r, suspicion=v) for r, v in zip(REGIONS, vals)]


def run(img_rgb: np.ndarray, face, case_dir: Path) -> Signal:
    cf, probe = 0.42, 0.88
    return Signal(id="classifier", name="Deepfake classifier (cf + face probe)", score=max(cf, probe),
                  reason="Face-crop probe scores 0.88 (face-swap pattern); full-image detector scores 0.42.",
                  details={"cf": cf, "probe": probe})
