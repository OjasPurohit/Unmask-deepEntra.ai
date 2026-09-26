"""
core/test_explain.py

Manual smoke test for core/explain.py on a single image.

Loads test_data/fake/fake_3.jpg (fake_1.jpg has no human face, see core/test_face.py),
runs the full explainability pipeline (region attribution + spatial occlusion
heatmap) via core.explain.get_explainability(), saves the visualization and
raw JSON, and prints a report.

Run:
    python core/test_explain.py
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.explain import get_explainability, REGION_LABELS

IMAGE_PATH = PROJECT_ROOT / "test_data" / "fake" / "fake_3.jpg"
OUTPUT_DIR = PROJECT_ROOT / "test_data" / "heatmaps" / "fake"


def main() -> None:
    print("=" * 60)
    print("S1 EXPLAINABILITY TEST")
    print("=" * 60)

    print(f"\nImage: {IMAGE_PATH.name}")

    start = time.perf_counter()
    result = get_explainability(IMAGE_PATH, OUTPUT_DIR)
    total_elapsed = time.perf_counter() - start

    print(f"\nOriginal S1 fake probability: {result['baseline_score'] * 100:.2f}%")

    print("\nREGION ATTRIBUTION")
    print("-" * 60)

    region_attributions = result["region_attributions"]
    if not region_attributions:
        print("(unavailable: no face regions detected)")
    else:
        for key, label in REGION_LABELS.items():
            if key in region_attributions:
                value = region_attributions[key]
                print(f"{label + ':':<15}{value:+.2f}")
            else:
                print(f"{label + ':':<15}(no mask)")

    print("\nTOP CONTRIBUTING REGIONS")
    print("-" * 60)

    top_regions = result["top_regions"]
    if not top_regions:
        print("(none — no face regions detected)")
    else:
        for i, entry in enumerate(top_regions[:3], start=1):
            name = entry["region"]
            value = entry["attribution"]
            direction = "toward FAKE" if value >= 0 else "toward REAL"
            print(f"{i}. {REGION_LABELS.get(name, name)} ({value:+.2f}, {direction})")

    grid = result["heatmap_data"]["attributions"]
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    flat = [v for row in grid for v in row]

    print("\nSPATIAL HEATMAP")
    print("-" * 60)
    print(f"Grid: {rows}x{cols}")
    print(f"Highest contribution: {max(flat) * 100:+.2f}%")
    print(f"Lowest contribution:  {min(flat) * 100:+.2f}%")

    print(f"\nHeatmap saved to:\n{result['heatmap_image']}")
    print(f"\nHeatmap data saved to:\n{OUTPUT_DIR / (IMAGE_PATH.stem + '_heatmap.json')}")

    print(f"\nExecution time:\n{total_elapsed:.2f}s")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
