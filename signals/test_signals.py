"""
signals/test_signals.py

Unified test for all four independent forensic signals (ELA, FFT, Noise
Residual, Metadata) over test_data/real/ and test_data/fake/.

Does NOT run S1, does NOT fuse the signals into one score. Each signal
is printed and analyzed independently, exactly as CLAUDE.md's signal
contract intends ("every signal is independent and pure").

Run:
    python signals/test_signals.py
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from signals import ela, fft, noise, metadata

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

REAL_DIR = PROJECT_ROOT / "test_data" / "real"
FAKE_DIR = PROJECT_ROOT / "test_data" / "fake"

SIGNAL_MODULES = [
    ("ELA", ela),
    ("FFT", fft),
    ("Noise Residual", noise),
    ("Metadata", metadata),
]


def _list_images(folder: Path) -> list:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _format_score(score) -> str:
    if score is None:
        return "  N/A  "
    return f"{score * 100:.2f}%"


def _run_all_signals(image_path: Path) -> dict:
    """Run all four signals on one image. A failing signal never stops the others."""

    results = {}
    for label, module in SIGNAL_MODULES:
        results[label] = module.analyze(image_path=str(image_path))
    return results


def _process_folder(folder: Path, label: str) -> list:
    print(f"\n{label}")
    print("-" * 60)

    rows = []

    for image_path in _list_images(folder):
        print(f"\n{image_path.name}")

        results = _run_all_signals(image_path)

        for signal_label, _ in SIGNAL_MODULES:
            r = results[signal_label]
            print(f"  {signal_label + ':':<17}{_format_score(r['score'])}")

        for signal_label, _ in SIGNAL_MODULES:
            viz = results[signal_label]["visualization"]
            if viz:
                print(f"    {signal_label} visualization: {viz}")

        rows.append({"name": image_path.name, "results": results})

    return rows


def _group_stats(rows: list, signal_label: str) -> dict:
    scores = [r["results"][signal_label]["score"] for r in rows]
    scores = [s for s in scores if s is not None]

    if not scores:
        return {"n": 0, "mean": None, "min": None, "max": None}

    return {
        "n": len(scores),
        "mean": sum(scores) / len(scores),
        "min": min(scores),
        "max": max(scores),
    }


def main() -> None:
    print("=" * 60)
    print("FORENSIC SIGNAL TEST")
    print("=" * 60)

    start = time.perf_counter()

    real_rows = _process_folder(REAL_DIR, "REAL IMAGES")
    fake_rows = _process_folder(FAKE_DIR, "FAKE IMAGES")

    elapsed = time.perf_counter() - start

    print("\n" + "=" * 60)
    print("CALIBRATION SUMMARY (engineering anomaly scores, NOT validated)")
    print("=" * 60)

    for signal_label, _ in SIGNAL_MODULES:
        real_stats = _group_stats(real_rows, signal_label)
        fake_stats = _group_stats(fake_rows, signal_label)

        print(f"\n{signal_label}")

        if real_stats["n"] == 0:
            print("  REAL: no valid scores")
        else:
            print(
                f"  REAL: mean={real_stats['mean'] * 100:.2f}%  "
                f"min={real_stats['min'] * 100:.2f}%  max={real_stats['max'] * 100:.2f}%  "
                f"(n={real_stats['n']})"
            )

        if fake_stats["n"] == 0:
            print("  FAKE: no valid scores")
        else:
            print(
                f"  FAKE: mean={fake_stats['mean'] * 100:.2f}%  "
                f"min={fake_stats['min'] * 100:.2f}%  max={fake_stats['max'] * 100:.2f}%  "
                f"(n={fake_stats['n']})"
            )

        if real_stats["mean"] is not None and fake_stats["mean"] is not None:
            gap = fake_stats["mean"] - real_stats["mean"]
            direction = "higher on FAKE" if gap > 0 else "higher on REAL" if gap < 0 else "no difference"
            print(f"  Mean gap (fake - real): {gap * 100:+.2f} pts -> {direction}")

    total_images = len(real_rows) + len(fake_rows)
    print(f"\nTotal images processed: {total_images}")
    print(f"Total execution time: {elapsed:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
