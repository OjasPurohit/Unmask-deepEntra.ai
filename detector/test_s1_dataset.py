import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
from detector.s1_ensemble import predict_s1


REAL_DIR = PROJECT_ROOT / "test_data" / "real"
FAKE_DIR = PROJECT_ROOT / "test_data" / "fake"


def analyze_folder(folder, actual_label):
    results = []

    image_files = sorted(
        list(folder.glob("*.jpg")) +
        list(folder.glob("*.jpeg")) +
        list(folder.glob("*.png"))
    )

    for image_path in image_files:

        image = Image.open(image_path).convert("RGB")

        result = predict_s1(image)

        fake_score = result["score"]
        real_score = 1 - fake_score

        if fake_score >= 0.5:
            prediction = "FAKE"
            confidence = fake_score
        else:
            prediction = "REAL"
            confidence = real_score

        correct = prediction == actual_label

        print(
            f"{image_path.name} → "
            f"{prediction} confidence {confidence * 100:.2f}%"
        )

        results.append({
            "name": image_path.name,
            "actual": actual_label,
            "score": fake_score,
            "prediction": prediction,
            "confidence": confidence,
            "correct": correct,
        })

    return results


print("=" * 60)
print("S1 ENSEMBLE RESULTS")
print("=" * 60)

print("\nREAL IMAGES")
print("-" * 60)

real_results = analyze_folder(REAL_DIR, "REAL")

print("\nFAKE IMAGES")
print("-" * 60)

fake_results = analyze_folder(FAKE_DIR, "FAKE")

results = real_results + fake_results


# Metrics
total = len(results)
correct = sum(r["correct"] for r in results)

accuracy = correct / total if total else 0

true_positive = sum(
    r["actual"] == "FAKE" and r["prediction"] == "FAKE"
    for r in results
)

true_negative = sum(
    r["actual"] == "REAL" and r["prediction"] == "REAL"
    for r in results
)

false_positive = sum(
    r["actual"] == "REAL" and r["prediction"] == "FAKE"
    for r in results
)

false_negative = sum(
    r["actual"] == "FAKE" and r["prediction"] == "REAL"
    for r in results
)


print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

print(f"Total images: {total}")
print(f"Correct:      {correct}")
print(f"Accuracy:     {accuracy * 100:.2f}%")

print("\nConfusion Matrix")
print(f"True Positives:  {true_positive}")
print(f"True Negatives:  {true_negative}")
print(f"False Positives: {false_positive}")
print(f"False Negatives: {false_negative}")

print("=" * 60)