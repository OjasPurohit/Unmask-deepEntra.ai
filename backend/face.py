"""Face detection + crop + region masks. OWNER: Omkar. STUB: centered square box."""
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class FaceInfo:
    box: tuple[int, int, int, int]          # x, y, w, h (1.3x landmark box)
    crop: np.ndarray                        # 224x224 RGB face crop
    landmarks: np.ndarray | None = None     # (478, 2) pixel coords
    masks: dict[str, np.ndarray] = field(default_factory=dict)  # region -> bool mask, full image size
    n_faces: int = 1
    yaw: float = 0.0


def detect(img: np.ndarray) -> FaceInfo | None:
    h, w = img.shape[:2]
    s = int(min(h, w) * 0.6)
    x, y = (w - s) // 2, (h - s) // 2
    crop = cv2.resize(img[y:y + s, x:x + s], (224, 224))
    return FaceInfo(box=(x, y, s, s), crop=crop)
