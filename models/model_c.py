import torch
import timm
import albumentations as A
import numpy as np

from PIL import Image
from huggingface_hub import hf_hub_download
from albumentations.pytorch import ToTensorV2


MODEL_NAME = "Arko007/deepfake-image-detector"

# --------------------------------------------------
# Device
# --------------------------------------------------

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# --------------------------------------------------
# Load checkpoint
# --------------------------------------------------

print(f"[Model C] Loading on {device}...")

checkpoint_path = hf_hub_download(
    repo_id=MODEL_NAME,
    filename="pytorch_model.bin"
)

print(f"[Model C] Checkpoint: {checkpoint_path}")


# --------------------------------------------------
# Create EfficientNetV2-S
# --------------------------------------------------

model = timm.create_model(
    "tf_efficientnetv2_s",
    pretrained=False,
    num_classes=1
)


# --------------------------------------------------
# Load checkpoint
# --------------------------------------------------

checkpoint = torch.load(
    checkpoint_path,
    map_location="cpu"
)

if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
    checkpoint = checkpoint["state_dict"]


# --------------------------------------------------
# Remove prefixes
# --------------------------------------------------

clean_checkpoint = {}

for key, value in checkpoint.items():

    if key.startswith("backbone."):
        key = key.replace("backbone.", "", 1)

    if key.startswith("module."):
        key = key.replace("module.", "", 1)

    clean_checkpoint[key] = value


# --------------------------------------------------
# Separate backbone and classifier
# --------------------------------------------------

backbone_state = {}
classifier_state = {}

for key, value in clean_checkpoint.items():

    if key.startswith("classifier."):

        new_key = key.replace("classifier.", "", 1)

        classifier_state[new_key] = value

    else:

        backbone_state[key] = value


# --------------------------------------------------
# Load backbone
# --------------------------------------------------

missing, unexpected = model.load_state_dict(
    backbone_state,
    strict=False
)


# --------------------------------------------------
# Exact classifier structure
# --------------------------------------------------

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


# --------------------------------------------------
# Load classifier weights
# --------------------------------------------------

classifier.load_state_dict(
    classifier_state,
    strict=True
)


# Replace timm classifier
model.classifier = classifier


# --------------------------------------------------
# GPU
# --------------------------------------------------

model = model.to(device)
model.eval()


# --------------------------------------------------
# Image preprocessing
# --------------------------------------------------

transform = A.Compose([

    A.Resize(380, 380),

    A.Normalize(
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225)
    ),

    ToTensorV2()
])


# --------------------------------------------------
# Prediction
# --------------------------------------------------

def predict_model_c(image):
    """
    Run Model C on a PIL image.

    Returns:
        float: fake probability between 0 and 1
    """

    # Make sure image is RGB
    image = image.convert("RGB")

    # PIL → NumPy
    image_array = np.array(image)

    # Apply exact preprocessing
    transformed = transform(
        image=image_array
    )

    tensor = transformed["image"]

    # Add batch dimension and move to GPU
    tensor = tensor.unsqueeze(0).to(device)

    # Inference
    with torch.inference_mode():

        output = model(tensor)

        fake_probability = torch.sigmoid(
            output.squeeze()
        ).item()

    return fake_probability