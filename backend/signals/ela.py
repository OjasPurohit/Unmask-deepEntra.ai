"""S2: error level analysis. OWNER: Yadnesh. STUB."""
from pathlib import Path

import numpy as np

from backend.schemas import Signal


def run(img_rgb: np.ndarray, face, case_dir: Path) -> Signal:
    return Signal(id="ela", name="Error level analysis", score=0.64,
                  reason="Face region re-compresses 2.1x more strongly than the background.", details={})
