import torch
from PIL import Image
from transformers import ViTForImageClassification, ViTImageProcessor


MODEL_NAME = "buildborderless/CommunityForensics-DeepfakeDet-ViT"

# --------------------------------------------------
# Device
# --------------------------------------------------

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# --------------------------------------------------
# Load processor and model once
# --------------------------------------------------

print(f"[Model A] Loading on {device}...")

processor = ViTImageProcessor.from_pretrained(MODEL_NAME)

model = ViTForImageClassification.from_pretrained(MODEL_NAME)

model = model.to(device)
model.eval()

print("[Model A] Loaded successfully.")


# --------------------------------------------------
# Prediction
# --------------------------------------------------

def predict_model_a(image):
    """
    Run Model A on a PIL image.

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

    # Model A has one output logit
    logit = outputs.logits[0, 0]

    # Convert logit to fake probability
    fake_probability = torch.sigmoid(logit).item()

    return fake_probability