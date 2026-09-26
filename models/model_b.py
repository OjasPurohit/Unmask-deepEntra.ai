import torch
from PIL import Image
from transformers import AutoImageProcessor, SiglipForImageClassification


MODEL_NAME = "prithivMLmods/deepfake-detector-model-v1"

# --------------------------------------------------
# Device
# --------------------------------------------------

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# --------------------------------------------------
# Load processor and model once
# --------------------------------------------------

print(f"[Model B] Loading on {device}...")

processor = AutoImageProcessor.from_pretrained(MODEL_NAME)

model = SiglipForImageClassification.from_pretrained(MODEL_NAME)

model = model.to(device)
model.eval()

print("[Model B] Loaded successfully.")


# --------------------------------------------------
# Prediction
# --------------------------------------------------

def predict_model_b(image):
    """
    Run Model B on a PIL image.

    Returns:
        float: fake probability between 0 and 1
    """

    # Make sure image is RGB
    image = image.convert("RGB")

    # Preprocess
    inputs = processor(
        images=image,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    # Inference
    with torch.inference_mode():
        outputs = model(**inputs)

    # Model B:
    # class 0 = Fake
    # class 1 = Real

    probabilities = torch.softmax(outputs.logits, dim=1)[0]

    fake_probability = probabilities[0].item()

    return fake_probability