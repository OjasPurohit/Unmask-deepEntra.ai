"""
core/test_explain_dataset.py

Runs the S1 explainability pipeline (core.explain.get_explainability) over
every image in test_data/real/ and test_data/fake/, saving a heatmap image
+ JSON for each into test_data/heatmaps/{real,fake}/, and printing progress
plus a summary. Never crashes on a single bad/faceless image -- failures
are caught, counted, and reported at the end.

Run:
    python core/test_explain_dataset.py
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.explain import get_explainability, REGION_LABELS

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

REAL_DIR = PROJECT_ROOT / "test_data" / "real"
FAKE_DIR = PROJECT_ROOT / "test_data" / "fake"

HEATMAP_ROOT = PROJECT_ROOT / "test_data" / "heatmaps"
REAL_OUT_DIR = HEATMAP_ROOT / "real"
FAKE_OUT_DIR = HEATMAP_ROOT / "fake"


def _list_images(folder: Path) -> list:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _process_folder(folder: Path, out_dir: Path, label: str) -> dict:
    print(f"\n{label}")
    print("-" * 60)

    out_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    generated = 0
    failed = 0

    for image_path in _list_images(folder):
        print(image_path.name)

        processed += 1
        try:
            result = get_explainability(image_path, out_dir)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failed += 1
            continue

        top_region = result["top_regions"][0]["region"] if result["top_regions"] else None
        top_region_label = REGION_LABELS.get(top_region, top_region) if top_region else "(none — no face regions)"

        print(f"  S1 score: {result['baseline_score'] * 100:.2f}%")
        print(f"  Top region: {top_region_label}")
        print(f"  Heatmap: {result['heatmap_image']}")

        generated += 1

    return {"processed": processed, "generated": generated, "failed": failed}


def main() -> None:
    print("=" * 60)
    print("S1 EXPLAINABILITY DATASET TEST")
    print("=" * 60)

    start = time.perf_counter()

    real_stats = _process_folder(REAL_DIR, REAL_OUT_DIR, "REAL IMAGES")
    fake_stats = _process_folder(FAKE_DIR, FAKE_OUT_DIR, "FAKE IMAGES")

    elapsed = time.perf_counter() - start

    total_processed = real_stats["processed"] + fake_stats["processed"]
    total_generated = real_stats["generated"] + fake_stats["generated"]
    total_failed = real_stats["failed"] + fake_stats["failed"]

    print("\n" + "=" * 60)
    print("HEATMAP GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nImages processed: {total_processed}")
    print(f"Heatmaps generated: {total_generated}")
    print(f"Failed: {total_failed}")
    print(f"\nTotal execution time: {elapsed:.2f}s")
    print("\nOutput directories:")
    print(f"  {REAL_OUT_DIR}")
    print(f"  {FAKE_OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
