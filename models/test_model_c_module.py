from PIL import Image

from model_c import predict_model_c


IMAGE_PATH = "../test_data/fake/fake_1.jpg"


image = Image.open(IMAGE_PATH).convert("RGB")

score = predict_model_c(image)

print("=" * 50)
print("MODEL C MODULE TEST")
print("=" * 50)

print(f"Fake probability: {score * 100:.2f}%")
print(f"Real probability: {(1 - score) * 100:.2f}%")

if score >= 0.5:
    print("Potentially manipulated")
else:
    print("Likely authentic")