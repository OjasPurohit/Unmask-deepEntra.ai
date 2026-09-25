import torch
from PIL import Image
from transformers import AutoImageProcessor, SiglipForImageClassification

MODEL_NAME = "prithivMLmods/deepfake-detector-model-v1"

IMAGE_PATH = "test_data/fake/fake_1.jpg"

print("===================================")
print(" Model B - Deepfake Detector Test")
print("===================================")

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Device:", device)

print("\nLoading processor...")
processor = AutoImageProcessor.from_pretrained(MODEL_NAME)

print("Loading model...")
model = SiglipForImageClassification.from_pretrained(MODEL_NAME)

model = model.to(device)
model.eval()

print("Model loaded!")

print("\nLoading image...")
image = Image.open(IMAGE_PATH).convert("RGB")

inputs = processor(
    images=image,
    return_tensors="pt"
)

inputs = {
    key: value.to(device)
    for key, value in inputs.items()
}

print("Running prediction...")

with torch.no_grad():
    outputs = model(**inputs)

probabilities = torch.softmax(outputs.logits, dim=1)[0]

fake_probability = probabilities[0].item()
real_probability = probabilities[1].item()

print("\n===================================")
print(" RESULT")
print("===================================")

print(f"Fake probability: {fake_probability * 100:.2f}%")
print(f"Real probability: {real_probability * 100:.2f}%")

if fake_probability >= real_probability:
    print("Prediction: POTENTIALLY FAKE")
else:
    print("Prediction: LIKELY REAL")

print("===================================")