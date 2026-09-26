"""S4: noise residual face vs background. OWNER: Yadnesh. STUB."""
from pathlib import Path

import numpy as np

from backend.schemas import Signal


def run(img_rgb: np.ndarray, face, case_dir: Path) -> Signal:
    return Signal(id="noise", name="Noise residual", score=0.71,
                  reason="Face noise level differs from the background by 58%.", details={})
