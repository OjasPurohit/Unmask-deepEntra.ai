import torch
import timm
import albumentations as A
import numpy as np

from PIL import Image
from huggingface_hub import hf_hub_download
from albumentations.pytorch import ToTensorV2


MODEL_NAME = "Arko007/deepfake-image-detector"
IMAGE_PATH = "test_data/fake/fake_1.jpg"

device = "cuda" if torch.cuda.is_available() else "cpu"


print("===================================")
print(" Model C - Deepfake Image Detector")
print("===================================")
print("Device:", device)


# ==================================================
# DOWNLOAD CHECKPOINT
# ==================================================

print("\nDownloading/loading checkpoint...")

checkpoint_path = hf_hub_download(
    repo_id=MODEL_NAME,
    filename="pytorch_model.bin"
)

print("Checkpoint:", checkpoint_path)


# ==================================================
# CREATE EFFICIENTNETV2-S
# ==================================================

print("\nCreating EfficientNetV2-S model...")

model = timm.create_model(
    "tf_efficientnetv2_s",
    pretrained=False,
    num_classes=1
)


# ==================================================
# LOAD CHECKPOINT
# ==================================================

checkpoint = torch.load(
    checkpoint_path,
    map_location="cpu"
)

if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
    checkpoint = checkpoint["state_dict"]


# Remove backbone prefix
clean_checkpoint = {}

for key, value in checkpoint.items():

    if key.startswith("backbone."):
        key = key.replace("backbone.", "", 1)

    if key.startswith("module."):
        key = key.replace("module.", "", 1)

    clean_checkpoint[key] = value


# ==================================================
# SEPARATE BACKBONE AND CLASSIFIER
# ==================================================

backbone_state = {}
classifier_state = {}

for key, value in clean_checkpoint.items():

    if key.startswith("classifier."):

        # Remove classifier. prefix
        new_key = key.replace("classifier.", "", 1)

        classifier_state[new_key] = value

    else:

        backbone_state[key] = value


print("\nBackbone parameters:", len(backbone_state))
print("Classifier parameters:", len(classifier_state))


# ==================================================
# LOAD BACKBONE
# ==================================================

print("\nLoading EfficientNet backbone...")

missing, unexpected = model.load_state_dict(
    backbone_state,
    strict=False
)

print("Backbone loaded.")


# ==================================================
# CREATE EXACT CLASSIFIER STRUCTURE
# ==================================================

print("\nCreating classifier...")


classifier = torch.nn.Sequential(

    # 0
    torch.nn.Linear(1280, 1024),

    # 1
    torch.nn.BatchNorm1d(1024),

    # 2
    torch.nn.ReLU(),

    # 3
    torch.nn.Dropout(0.3),

    # 4
    torch.nn.Linear(1024, 512),

    # 5
    torch.nn.BatchNorm1d(512),

    # 6
    torch.nn.ReLU(),

    # 7
    torch.nn.Dropout(0.3),

    # 8
    torch.nn.Linear(512, 256),

    # 9
    torch.nn.BatchNorm1d(256),

    # 10
    torch.nn.ReLU(),

    # 11
    torch.nn.Dropout(0.3),

    # 12
    torch.nn.Linear(256, 1)
)


# ==================================================
# LOAD CLASSIFIER WEIGHTS
# ==================================================

classifier.load_state_dict(
    classifier_state,
    strict=True
)

print("Classifier loaded successfully.")


# Replace timm classifier
model.classifier = classifier


# ==================================================
# GPU
# ==================================================

model = model.to(device)
model.eval()


# ==================================================
# IMAGE PREPROCESSING
# ==================================================

transform = A.Compose([

    A.Resize(380, 380),

    A.Normalize(
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225)
    ),

    ToTensorV2()
])


# ==================================================
# LOAD IMAGE
# ==================================================

print("\nLoading image...")

image = Image.open(
    IMAGE_PATH
).convert("RGB")

image = np.array(image)


transformed = transform(
    image=image
)

tensor = transformed["image"]

tensor = tensor.unsqueeze(0).to(device)


# ==================================================
# PREDICTION
# ==================================================

print("Running prediction...")

with torch.no_grad():

    output = model(tensor)

    fake_probability = torch.sigmoid(
        output.squeeze()
    ).item()


real_probability = 1 - fake_probability


# ==================================================
# RESULT
# ==================================================

print("\n===================================")
print(" RESULT")
print("===================================")

print(
    f"Fake probability: "
    f"{fake_probability * 100:.2f}%"
)

print(
    f"Real probability: "
    f"{real_probability * 100:.2f}%"
)

if fake_probability >= 0.50:

    print("Prediction: POTENTIALLY FAKE")

else:

    print("Prediction: LIKELY REAL")

print("===================================")