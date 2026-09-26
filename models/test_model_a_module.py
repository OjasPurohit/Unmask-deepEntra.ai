from PIL import Image

from model_a import predict_model_a


IMAGE_PATH = "../test_data/fake/fake_1.jpg"


image = Image.open(IMAGE_PATH).convert("RGB")

score = predict_model_a(image)

print("=" * 50)
print("MODEL A MODULE TEST")
print("=" * 50)

print(f"Fake probability: {score * 100:.2f}%")

if score >= 0.5:
    print("Potentially manipulated")
else:
    print("Likely authentic")