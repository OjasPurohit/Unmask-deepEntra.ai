import torch
import timm
import albumentations as A
import numpy as np

from pathlib import Path
from PIL import Image
from transformers import (
    ViTForImageClassification,
    ViTImageProcessor,
    AutoImageProcessor,
    AutoModelForImageClassification
)
from huggingface_hub import hf_hub_download
from albumentations.pytorch import ToTensorV2


# ============================================================
# CONFIG
# ============================================================

MODEL_A = "buildborderless/CommunityForensics-DeepfakeDet-ViT"
MODEL_B = "prithivMLmods/deepfake-detector-model-v1"
MODEL_C = "Arko007/deepfake-image-detector"

TEST_DIR = Path("test_data")

device = "cuda" if torch.cuda.is_available() else "cpu"

print("==============================================")
print(" Deepfake Detector - Model Comparison")
print("==============================================")
print("Device:", device)


# ============================================================
# MODEL A
# ============================================================

print("\nLoading Model A...")

processor_a = ViTImageProcessor.from_pretrained(MODEL_A)

model_a = ViTForImageClassification.from_pretrained(
    MODEL_A
)

model_a = model_a.to(device)
model_a.eval()

print("Model A loaded.")


# ============================================================
# MODEL B
# ============================================================

print("\nLoading Model B...")

processor_b = AutoImageProcessor.from_pretrained(
    MODEL_B
)

model_b = AutoModelForImageClassification.from_pretrained(
    MODEL_B
)

model_b = model_b.to(device)
model_b.eval()

print("Model B loaded.")


# ============================================================
# MODEL C
# ============================================================

print("\nLoading Model C...")

checkpoint_path = hf_hub_download(
    repo_id=MODEL_C,
    filename="pytorch_model.bin"
)

print("Model C checkpoint:", checkpoint_path)

model_c = timm.create_model(
    "tf_efficientnetv2_s",
    pretrained=False,
    num_classes=1
)

checkpoint = torch.load(
    checkpoint_path,
    map_location="cpu"
)

if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
    checkpoint = checkpoint["state_dict"]


# Remove prefixes
clean_checkpoint = {}

for key, value in checkpoint.items():

    if key.startswith("backbone."):
        key = key.replace("backbone.", "", 1)

    if key.startswith("module."):
        key = key.replace("module.", "", 1)

    clean_checkpoint[key] = value


# Separate backbone and classifier
backbone_state = {}
classifier_state = {}

for key, value in clean_checkpoint.items():

    if key.startswith("classifier."):

        new_key = key.replace("classifier.", "", 1)

        classifier_state[new_key] = value

    else:

        backbone_state[key] = value


# Load backbone
model_c.load_state_dict(
    backbone_state,
    strict=False
)


# Exact classifier structure
classifier = torch.nn.Sequential(

    torch.nn.Linear(1280, 1024),
    torch.nn.BatchNorm1d(1024),
    torch.nn.ReLU(),
    torch.nn.Dropout(0.3),

    torch.nn.Linear(1024, 512),
    torch.nn.BatchNorm1d(512),
    torch.nn.ReLU(),
    torch.nn.Dropout(0.3),

    torch.nn.Linear(512, 256),
    torch.nn.BatchNorm1d(256),
    torch.nn.ReLU(),
    torch.nn.Dropout(0.3),

    torch.nn.Linear(256, 1)
)

classifier.load_state_dict(
    classifier_state,
    strict=True
)

model_c.classifier = classifier

model_c = model_c.to(device)
model_c.eval()

print("Model C loaded.")


# ============================================================
# MODEL C PREPROCESSING
# ============================================================

transform_c = A.Compose([

    A.Resize(380, 380),

    A.Normalize(
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225)
    ),

    ToTensorV2()
])


# ============================================================
# PREDICTION FUNCTIONS
# ============================================================

def predict_model_a(image):
    """
    Model A:
    sigmoid(logit) = fake probability
    """

    inputs = processor_a(
        images=image,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        output = model_a(**inputs)

        fake_probability = torch.sigmoid(
            output.logits.squeeze()
        ).item()

    return fake_probability


def predict_model_b(image):
    """
    Model B:
    class 0 = Fake
    class 1 = Real
    """

    inputs = processor_b(
        images=image,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        output = model_b(**inputs)

        probabilities = torch.softmax(
            output.logits,
            dim=-1
        )[0]

    fake_probability = probabilities[0].item()

    return fake_probability


def predict_model_c(image):
    """
    Model C:
    sigmoid(logit) = fake probability
    """

    image_array = np.array(
        image.convert("RGB")
    )

    transformed = transform_c(
        image=image_array
    )

    tensor = transformed["image"]

    tensor = tensor.unsqueeze(0).to(device)

    with torch.no_grad():

        output = model_c(tensor)

        fake_probability = torch.sigmoid(
            output.squeeze()
        ).item()

    return fake_probability


# ============================================================
# LOAD TEST IMAGES
# ============================================================

images = []

for label, folder in [
    ("REAL", TEST_DIR / "real"),
    ("FAKE", TEST_DIR / "fake")
]:

    for image_path in sorted(folder.glob("*")):

        if image_path.suffix.lower() not in [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        ]:
            continue

        images.append(
            (image_path, label)
        )


print("\n==============================================")
print(" Test Images:", len(images))
print("==============================================")


# ============================================================
# RUN ALL MODELS
# ============================================================

results = []

print("\nRunning all three models...\n")

for image_path, true_label in images:

    print("Processing:", image_path.name)

    image = Image.open(
        image_path
    ).convert("RGB")

    fake_a = predict_model_a(image)

    fake_b = predict_model_b(image)

    fake_c = predict_model_c(image)

    results.append({
        "image": image_path.name,
        "true": true_label,
        "A": fake_a,
        "B": fake_b,
        "C": fake_c
    })


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\n")
print("=" * 90)

print(
    f"{'IMAGE':<15}"
    f"{'TRUE':<10}"
    f"{'MODEL A':>15}"
    f"{'MODEL B':>15}"
    f"{'MODEL C':>15}"
)

print("=" * 90)


for result in results:

    print(
        f"{result['image']:<15}"
        f"{result['true']:<10}"
        f"{result['A'] * 100:>14.2f}%"
        f"{result['B'] * 100:>14.2f}%"
        f"{result['C'] * 100:>14.2f}%"
    )


print("=" * 90)


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    results,
    model_name,
    threshold=0.50
):

    tp = 0
    tn = 0
    fp = 0
    fn = 0

    for result in results:

        actual_fake = (
            result["true"] == "FAKE"
        )

        predicted_fake = (
            result[model_name] >= threshold
        )

        if actual_fake and predicted_fake:
            tp += 1

        elif not actual_fake and not predicted_fake:
            tn += 1

        elif not actual_fake and predicted_fake:
            fp += 1

        elif actual_fake and not predicted_fake:
            fn += 1


    total = tp + tn + fp + fn

    accuracy = (
        (tp + tn) / total
        if total else 0
    )

    precision = (
        tp / (tp + fp)
        if (tp + fp) else 0
    )

    recall = (
        tp / (tp + fn)
        if (tp + fn) else 0
    )

    f1 = (
        2 * precision * recall /
        (precision + recall)
        if (precision + recall)
        else 0
    )

    fpr = (
        fp / (fp + tn)
        if (fp + tn) else 0
    )

    fnr = (
        fn / (fn + tp)
        if (fn + tp) else 0
    )


    return {
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "FPR": fpr,
        "FNR": fnr
    }


# ============================================================
# PRINT METRICS
# ============================================================

print("\n")
print("==============================================")
print(" MODEL METRICS")
print("==============================================")


for model_name in ["A", "B", "C"]:

    metrics = calculate_metrics(
        results,
        model_name
    )

    print(f"\nMODEL {model_name}")

    print(
        f"TP:        {metrics['TP']}"
    )

    print(
        f"TN:        {metrics['TN']}"
    )

    print(
        f"FP:        {metrics['FP']}"
    )

    print(
        f"FN:        {metrics['FN']}"
    )

    print(
        f"Accuracy:  {metrics['Accuracy'] * 100:.2f}%"
    )

    print(
        f"Precision: {metrics['Precision'] * 100:.2f}%"
    )

    print(
        f"Recall:    {metrics['Recall'] * 100:.2f}%"
    )

    print(
        f"F1 Score:  {metrics['F1'] * 100:.2f}%"
    )

    print(
        f"FPR:       {metrics['FPR'] * 100:.2f}%"
    )

    print(
        f"FNR:       {metrics['FNR'] * 100:.2f}%"
    )


print("\n==============================================")
print(" Comparison complete")
print("==============================================")