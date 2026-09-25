import os
import torch
from PIL import Image
from transformers import AutoImageProcessor, SiglipForImageClassification

MODEL_NAME = "prithivMLmods/deepfake-detector-model-v1"

REAL_DIR = "test_data/real"
FAKE_DIR = "test_data/fake"

device = "cuda" if torch.cuda.is_available() else "cpu"

print("===================================")
print(" Model B - Full Dataset Evaluation")
print("===================================")
print("Device:", device)

print("\nLoading processor...")
processor = AutoImageProcessor.from_pretrained(MODEL_NAME)

print("Loading model...")
model = SiglipForImageClassification.from_pretrained(MODEL_NAME)
model = model.to(device)
model.eval()

print("Model loaded!\n")

results = []

def predict_image(image_path, actual_label):
    image = Image.open(image_path).convert("RGB")

    inputs = processor(
        images=image,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(outputs.logits, dim=1)[0]

    fake_probability = probabilities[0].item()

    predicted_label = 1 if fake_probability >= 0.50 else 0

    results.append({
        "file": os.path.basename(image_path),
        "actual": actual_label,
        "predicted": predicted_label,
        "fake_probability": fake_probability
    })

    prediction_text = "FAKE" if predicted_label == 1 else "REAL"

    print(
        f"{os.path.basename(image_path):20} "
        f"Fake: {fake_probability * 100:6.2f}%  "
        f"Prediction: {prediction_text}"
    )


print("========== REAL IMAGES ==========")

for filename in sorted(os.listdir(REAL_DIR)):
    path = os.path.join(REAL_DIR, filename)

    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        predict_image(path, actual_label=0)


print("\n========== FAKE IMAGES ==========")

for filename in sorted(os.listdir(FAKE_DIR)):
    path = os.path.join(FAKE_DIR, filename)

    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        predict_image(path, actual_label=1)


# -----------------------------
# Calculate confusion matrix
# -----------------------------

TP = sum(
    1 for r in results
    if r["actual"] == 1 and r["predicted"] == 1
)

TN = sum(
    1 for r in results
    if r["actual"] == 0 and r["predicted"] == 0
)

FP = sum(
    1 for r in results
    if r["actual"] == 0 and r["predicted"] == 1
)

FN = sum(
    1 for r in results
    if r["actual"] == 1 and r["predicted"] == 0
)

total = len(results)

accuracy = (TP + TN) / total if total else 0

precision = TP / (TP + FP) if (TP + FP) else 0

recall = TP / (TP + FN) if (TP + FN) else 0

f1 = (
    2 * precision * recall / (precision + recall)
    if (precision + recall)
    else 0
)

false_positive_rate = (
    FP / (FP + TN)
    if (FP + TN)
    else 0
)

false_negative_rate = (
    FN / (FN + TP)
    if (FN + TP)
    else 0
)


print("\n===================================")
print(" MODEL B RESULTS")
print("===================================")

print(f"Total images:        {total}")

print()
print(f"TP:                  {TP}")
print(f"TN:                  {TN}")
print(f"FP:                  {FP}")
print(f"FN:                  {FN}")

print()
print(f"Accuracy:            {accuracy * 100:.2f}%")
print(f"Precision:           {precision * 100:.2f}%")
print(f"Recall:              {recall * 100:.2f}%")
print(f"F1 Score:            {f1 * 100:.2f}%")
print(f"False Positive Rate: {false_positive_rate * 100:.2f}%")
print(f"False Negative Rate: {false_negative_rate * 100:.2f}%")

print("===================================")