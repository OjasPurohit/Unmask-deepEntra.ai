import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
from detector.s1_ensemble import predict_s1


IMAGE_PATH = PROJECT_ROOT / "test_data" / "fake" / "fake_1.jpg"


print("=" * 60)
print("S1 DEEP LEARNING ENSEMBLE TEST")
print("=" * 60)

print(f"\nLoading image: {IMAGE_PATH}")

image = Image.open(IMAGE_PATH).convert("RGB")

print(f"Image size: {image.size}")

print("\nRunning Model A + Model B + Model C...")

result = predict_s1(image)

score = result["score"]
score_a = result["model_a"]
score_b = result["model_b"]
score_c = result["model_c"]


print("\n" + "=" * 60)
print("INDIVIDUAL MODEL RESULTS")
print("=" * 60)

print(f"Model A (ViT):             {score_a * 100:.2f}%")
print(f"Model B (SigLIP):          {score_b * 100:.2f}%")
print(f"Model C (EfficientNet):    {score_c * 100:.2f}%")

print("\n" + "=" * 60)
print("S1 ENSEMBLE RESULT")
print("=" * 60)

print(f"S1 Fake Probability:       {score * 100:.2f}%")
print(f"S1 Real Probability:       {(1 - score) * 100:.2f}%")

if score < 0.35:
    print("Band: NO STRONG INDICATORS")
elif score <= 0.70:
    print("Band: INCONCLUSIVE")
else:
    print("Band: STRONG MANIPULATION INDICATORS")

print("=" * 60)