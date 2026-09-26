"""
signals/test_metadata.py

Prints the ExifTool-style metadata report + file-integrity digest for one
image, and confirms the existing metadata anomaly score (signals.metadata.analyze)
still works unchanged, separately from the new report.

Run:
    python signals/test_metadata.py
    python signals/test_metadata.py test_data/fake/fake_2.jpg
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from signals import metadata

DEFAULT_IMAGE = PROJECT_ROOT / "test_data" / "fake" / "fake_2.jpg"


MAP_OUTPUT_DIR = PROJECT_ROOT / "test_data" / "metadata_maps"


def main() -> None:
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IMAGE

    print(f"Analyzing: {image_path}\n")

    # Full forensic report: File/JPEG/JFIF/Composite/EXIF/GPS/Digest.
    # Generates a location map only if the image actually has GPS EXIF.
    report = metadata.print_forensic_report(str(image_path), map_output_dir=str(MAP_OUTPUT_DIR))

    # The existing metadata anomaly score is unchanged and kept separate
    # from the report above -- it is evidence/detail, not a replacement.
    result = metadata.analyze(image_path=str(image_path))
    print("\nEXISTING METADATA SIGNAL (unchanged)")
    print("-" * 60)
    score = result["score"]
    print(f"Score:  {'N/A' if score is None else f'{score * 100:.2f}%'}")
    print(f"Reason: {result['reason']}")

    print("\n" + "=" * 60)
    print("METADATA + DIGEST TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
