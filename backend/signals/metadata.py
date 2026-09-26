"""S5: EXIF / software tags / C2PA presence. OWNER: Yadnesh. STUB."""
from pathlib import Path

import numpy as np

from backend.schemas import Signal


def run(img_rgb: np.ndarray, face, case_dir: Path) -> Signal:
    return Signal(id="metadata", name="Metadata & provenance", score=0.2,
                  reason="No camera EXIF; image appears re-encoded.", details={})
