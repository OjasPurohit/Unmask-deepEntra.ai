import os
import time
import torch
from PIL import Image
from transformers import (
    ViTForImageClassification,
    ViTImageProcessor
)

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "buildborderless/CommunityForensics-DeepfakeDet-ViT"

REAL_DIR = "test_data/real"
FAKE_DIR = "test_data/fake"

THRESHOLD = 0.50

# ============================================================
# DEVICE
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("COMMUNITY FORENSICS - MODEL EVALUATION")
print("=" * 70)

print(f"\nDevice: {device}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading model...")

processor = ViTImageProcessor.from_pretrained(
    MODEL_NAME
)

model = ViTForImageClassification.from_pretrained(
    MODEL_NAME
)

model = model.to(device)
model.eval()

print("Model loaded successfully.")

# ============================================================
# FUNCTION TO ANALYZE IMAGE
# ============================================================

def predict(image_path):

    image = Image.open(image_path).convert("RGB")

    inputs = processor(
        images=image,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    start = time.perf_counter()

    with torch.no_grad():
        outputs = model(**inputs)

    end = time.perf_counter()

    logit = outputs.logits[0, 0]

    fake_probability = torch.sigmoid(logit).item()

    inference_time = end - start

    prediction = (
        "FAKE"
        if fake_probability >= THRESHOLD
        else "REAL"
    )

    return fake_probability, prediction, inference_time


# ============================================================
# EVALUATE DATASET
# ============================================================

results = []

# ---------------------------
# REAL IMAGES
# ---------------------------

print("\n" + "-" * 70)
print("REAL IMAGES")
print("-" * 70)

for filename in sorted(os.listdir(REAL_DIR)):

    path = os.path.join(REAL_DIR, filename)

    if not os.path.isfile(path):
        continue

    try:

        probability, prediction, inference_time = predict(path)

        correct = prediction == "REAL"

        results.append({
            "actual": "REAL",
            "prediction": prediction,
            "fake_probability": probability,
            "correct": correct
        })

        status = "✓" if correct else "✗"

        print(
            f"{status} {filename:<25} "
            f"Fake probability: {probability * 100:6.2f}% "
            f"Prediction: {prediction}"
        )

    except Exception as e:

        print(f"ERROR processing {filename}: {e}")


# ---------------------------
# FAKE IMAGES
# ---------------------------

print("\n" + "-" * 70)
print("FAKE IMAGES")
print("-" * 70)

for filename in sorted(os.listdir(FAKE_DIR)):

    path = os.path.join(FAKE_DIR, filename)

    if not os.path.isfile(path):
        continue

    try:

        probability, prediction, inference_time = predict(path)

        correct = prediction == "FAKE"

        results.append({
            "actual": "FAKE",
            "prediction": prediction,
            "fake_probability": probability,
            "correct": correct
        })

        status = "✓" if correct else "✗"

        print(
            f"{status} {filename:<25} "
            f"Fake probability: {probability * 100:6.2f}% "
            f"Prediction: {prediction}"
        )

    except Exception as e:

        print(f"ERROR processing {filename}: {e}")


# ============================================================
# CALCULATE METRICS
# ============================================================

TP = 0
TN = 0
FP = 0
FN = 0

for result in results:

    actual = result["actual"]
    prediction = result["prediction"]

    if actual == "FAKE" and prediction == "FAKE":
        TP += 1

    elif actual == "REAL" and prediction == "REAL":
        TN += 1

    elif actual == "REAL" and prediction == "FAKE":
        FP += 1

    elif actual == "FAKE" and prediction == "REAL":
        FN += 1


total = TP + TN + FP + FN

accuracy = (TP + TN) / total if total else 0

precision = (
    TP / (TP + FP)
    if (TP + FP) > 0
    else 0
)

recall = (
    TP / (TP + FN)
    if (TP + FN) > 0
    else 0
)

f1 = (
    2 * precision * recall / (precision + recall)
    if (precision + recall) > 0
    else 0
)

false_positive_rate = (
    FP / (FP + TN)
    if (FP + TN) > 0
    else 0
)

false_negative_rate = (
    FN / (FN + TP)
    if (FN + TP) > 0
    else 0
)


# ============================================================
# RESULTS
# ============================================================

print("\n")
print("=" * 70)
print("EVALUATION RESULTS")
print("=" * 70)

print(f"""
Total images       : {total}

True Positives     : {TP}
True Negatives     : {TN}
False Positives    : {FP}
False Negatives    : {FN}

Accuracy           : {accuracy * 100:.2f}%
Precision          : {precision * 100:.2f}%
Recall             : {recall * 100:.2f}%
F1 Score           : {f1 * 100:.2f}%

False Positive Rate: {false_positive_rate * 100:.2f}%
False Negative Rate: {false_negative_rate * 100:.2f}%
""")

print("=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

print("""
                         PREDICTED
                    REAL          FAKE

ACTUAL REAL         TN            FP

ACTUAL FAKE         FN            TP
""")

print(f"                    {TN:<13} {FP}")
print(f"                    {FN:<13} {TP}")

print("=" * 70)