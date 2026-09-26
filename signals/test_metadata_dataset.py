"""
signals/test_metadata_dataset.py

Runs the full metadata + GPS + map + PDF pipeline over every image in
test_data/real/ and test_data/fake/. A failure on one image is caught,
counted, and does not stop the rest of the dataset from processing.

Run:
    python signals/test_metadata_dataset.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from signals import metadata
from signals.metadata_pdf import generate_metadata_pdf

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

REAL_DIR = PROJECT_ROOT / "test_data" / "real"
FAKE_DIR = PROJECT_ROOT / "test_data" / "fake"

REPORTS_ROOT = PROJECT_ROOT / "test_data" / "metadata_reports"
MAPS_ROOT = PROJECT_ROOT / "test_data" / "metadata_maps"


def _list_images(folder: Path) -> list:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _process_folder(folder: Path, subset: str, stats: dict) -> None:
    print(f"\n{subset.upper()} IMAGES")
    print("-" * 60)

    reports_dir = REPORTS_ROOT / subset
    maps_dir = MAPS_ROOT / subset

    for image_path in _list_images(folder):
        stats["processed"] += 1
        print(f"\n{image_path.name}")

        try:
            report = metadata.build_metadata_report(str(image_path), map_output_dir=str(maps_dir))

            exif = report.get("exif") or {}
            n_exif_fields = sum(1 for v in exif.values() if v is not None) if "error" not in exif else 0
            has_gps = bool(report["gps"]["present"])

            pdf_path = reports_dir / f"{image_path.stem}_metadata_report.pdf"
            generate_metadata_pdf(str(image_path), report, str(pdf_path))

            print("  metadata extracted successfully: Yes")
            print(f"  GPS present: {'Yes' if has_gps else 'No'}")
            print(f"  EXIF fields populated: {n_exif_fields}")
            print("  PDF generated successfully: Yes")

            stats["successful"] += 1
            if n_exif_fields > 0:
                stats["with_exif"] += 1
            if has_gps:
                stats["with_gps"] += 1
                if report["gps"].get("map_path"):
                    stats["maps_generated"] += 1
            stats["pdfs_generated"] += 1

        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            stats["failed"] += 1


def main() -> None:
    print("=" * 60)
    print("METADATA DATASET TEST")
    print("=" * 60)

    stats = {
        "processed": 0, "successful": 0, "failed": 0,
        "with_exif": 0, "with_gps": 0,
        "pdfs_generated": 0, "maps_generated": 0,
    }

    _process_folder(REAL_DIR, "real", stats)
    _process_folder(FAKE_DIR, "fake", stats)

    print("\n" + "=" * 60)
    print("METADATA DATASET SUMMARY")
    print("=" * 60)
    print(f"\nImages processed: {stats['processed']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Images with EXIF: {stats['with_exif']}")
    print(f"Images with GPS: {stats['with_gps']}")
    print(f"PDFs generated: {stats['pdfs_generated']}")
    print(f"Maps generated: {stats['maps_generated']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
