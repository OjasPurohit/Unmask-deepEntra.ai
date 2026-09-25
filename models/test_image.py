import torch
from PIL import Image
from transformers import ViTForImageClassification, ViTImageProcessor

MODEL_NAME = "buildborderless/CommunityForensics-DeepfakeDet-ViT"
IMAGE_PATH = "test.jpg"

# --------------------------------------------------
# 1. Device
# --------------------------------------------------

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 50)
print("COMMUNITY FORENSICS DEEPFAKE DETECTOR")
print("=" * 50)

print(f"\nDevice: {device}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# --------------------------------------------------
# 2. Load processor and model
# --------------------------------------------------

print("\nLoading model...")

processor = ViTImageProcessor.from_pretrained(MODEL_NAME)

model = ViTForImageClassification.from_pretrained(MODEL_NAME)

model = model.to(device)
model.eval()

print("Model loaded successfully.")

# --------------------------------------------------
# 3. Load image
# --------------------------------------------------

print(f"\nLoading image: {IMAGE_PATH}")

image = Image.open(IMAGE_PATH).convert("RGB")

print(f"Image size: {image.size}")

# --------------------------------------------------
# 4. Preprocess
# --------------------------------------------------

inputs = processor(
    images=image,
    return_tensors="pt"
)

inputs = {
    key: value.to(device)
    for key, value in inputs.items()
}

# --------------------------------------------------
# 5. Inference
# --------------------------------------------------

print("\nAnalyzing image...")

with torch.no_grad():
    outputs = model(**inputs)

logit = outputs.logits[0, 0]

# --------------------------------------------------
# 6. Convert logit to fake probability
# --------------------------------------------------

fake_probability = torch.sigmoid(logit).item()

real_probability = 1 - fake_probability

# --------------------------------------------------
# 7. Result
# --------------------------------------------------

print("\n" + "=" * 50)
print("RESULT")
print("=" * 50)

print(f"\nRaw model score : {logit.item():.4f}")

print(f"Fake probability : {fake_probability * 100:.2f}%")

print(f"Real probability : {real_probability * 100:.2f}%")

if fake_probability >= 0.5:
    print("\n⚠ POTENTIALLY MANIPULATED")
else:
    print("\n✓ LIKELY AUTHENTIC")

print("\nNOTE:")
print("This is a probabilistic AI estimate,")
print("not proof of authenticity or wrongdoing.")

print("=" * 50)