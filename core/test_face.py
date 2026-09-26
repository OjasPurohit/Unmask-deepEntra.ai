"""
core/test_face.py

Manual smoke test for core/face.py.

Loads test_data/fake/fake_1.jpg, runs detect_face(), prints a report, and
saves a visualization (bounding box + landmarks + region outlines) to
test_data/face_detection_test.jpg.

Run:
    python core/test_face.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
from PIL import Image

from core.face import detect_face

IMAGE_PATH = PROJECT_ROOT / "test_data" / "fake" / "fake_1.jpg"
OUTPUT_PATH = PROJECT_ROOT / "test_data" / "face_detection_test.jpg"

REGION_COLORS = {
    "face": (20, 180, 20),        # green
    "left_eye": (255, 0, 0),      # blue (BGR)
    "right_eye": (0, 0, 255),     # red
    "mouth": (0, 255, 255),       # yellow
    "nose": (255, 0, 255),        # magenta
    "jaw_boundary": (255, 140, 0),  # orange-ish
}


def main() -> None:
    print("=" * 60)
    print("FACE DETECTION TEST (core/face.py)")
    print("=" * 60)

    print(f"\nLoading image: {IMAGE_PATH}")
    image = Image.open(IMAGE_PATH).convert("RGB")
    width, height = image.size
    print(f"Image size: {width} x {height}")

    print("\nRunning detect_face()...")
    face = detect_face(image)

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)

    print(f"face_detected: {face.face_detected}")
    print(f"fallback_used: {face.fallback_used}")
    if face.limitation:
        print(f"limitation:    {face.limitation}")
    print(f"bbox:          {face.bbox}")
    print(f"confidence:    {face.confidence}")

    n_landmarks = 0 if face.landmarks is None else len(face.landmarks)
    print(f"num landmarks: {n_landmarks}")

    print("\nRegions detected:")
    if not face.regions:
        print("  (none)")
    for name, mask in face.regions.items():
        coverage_px = int(mask.sum())
        coverage_pct = 100.0 * coverage_px / (width * height)
        print(f"  {name:<14} pixels={coverage_px:<8} coverage={coverage_pct:.2f}%")

    # ------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------
    canvas = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR).copy()

    if face.bbox is not None:
        x_min, y_min, x_max, y_max = face.bbox
        cv2.rectangle(canvas, (x_min, y_min), (x_max, y_max), (255, 255, 255), 2)

    if face.landmarks is not None:
        for (x, y) in face.landmarks:
            cv2.circle(canvas, (int(x), int(y)), 1, (0, 255, 0), -1)

    for name, polygon in face.region_polygons.items():
        color = REGION_COLORS.get(name, (200, 200, 200))
        pts = np.round(polygon).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], isClosed=True, color=color, thickness=2)

    # jaw_boundary has no single polygon (it's a ring mask); draw its mask
    # as a semi-transparent overlay instead.
    if "jaw_boundary" in face.regions:
        overlay = canvas.copy()
        overlay[face.regions["jaw_boundary"]] = REGION_COLORS["jaw_boundary"]
        canvas = cv2.addWeighted(overlay, 0.5, canvas, 0.5, 0)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUTPUT_PATH), canvas)

    print(f"\nVisualization saved to: {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
