"""S3: frequency spectrum. OWNER: Yadnesh. STUB."""
from pathlib import Path

import numpy as np

from backend.schemas import Signal


def run(img_rgb: np.ndarray, face, case_dir: Path) -> Signal:
    return Signal(id="fft", name="Frequency spectrum", score=0.41,
                  reason="High-frequency energy slightly above the real-photo baseline.", details={})
