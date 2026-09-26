"""
signals/test_metadata_pdf.py

Builds the full forensic metadata report (with GPS/map when present) for
one image and renders it to a PDF via signals/metadata_pdf.py.

Run:
    python signals/test_metadata_pdf.py
    python signals/test_metadata_pdf.py test_data/fake/fake_2.jpg
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from signals import metadata
from signals.metadata_pdf import generate_metadata_pdf

DEFAULT_IMAGE = PROJECT_ROOT / "test_data" / "fake" / "fake_2.jpg"

REPORTS_DIR = PROJECT_ROOT / "test_data" / "metadata_reports"
MAPS_DIR = PROJECT_ROOT / "test_data" / "metadata_maps"


def _subset_for(image_path: Path) -> str:
    """real/ or fake/ if the image lives under test_data/{real,fake}/, else flat."""
    parts = {p.name for p in image_path.parents}
    if "real" in parts:
        return "real"
    if "fake" in parts:
        return "fake"
    return ""


def main() -> None:
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IMAGE

    subset = _subset_for(image_path)
    reports_dir = REPORTS_DIR / subset if subset else REPORTS_DIR
    maps_dir = MAPS_DIR / subset if subset else MAPS_DIR

    print("=" * 60)
    print("METADATA PDF TEST")
    print("=" * 60)

    print(f"\nImage:\n{image_path}")

    report = metadata.build_metadata_report(str(image_path), map_output_dir=str(maps_dir))

    gps_present = report["gps"]["present"]
    print(f"\nGPS:\n{'Present' if gps_present else 'Not available'}")
    if gps_present and report["gps"].get("map_path"):
        print(f"\nMap generated:\n{report['gps']['map_path']}")

    pdf_path = reports_dir / f"{image_path.stem}_metadata_report.pdf"
    generate_metadata_pdf(str(image_path), report, str(pdf_path))

    print(f"\nPDF generated:\n{pdf_path}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
