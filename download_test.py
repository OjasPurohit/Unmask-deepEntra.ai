import torch
from transformers import ViTForImageClassification, ViTImageProcessor

MODEL_NAME = "buildborderless/CommunityForensics-DeepfakeDet-ViT"

print("===================================")
print(" CommunityForensics Model Test")
print("===================================")

print("Loading processor...")
processor = ViTImageProcessor.from_pretrained(MODEL_NAME)

print("Loading model...")
model = ViTForImageClassification.from_pretrained(MODEL_NAME)

print("Model downloaded and loaded!")

print()
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

print()
print("Model type:", type(model).__name__)
print("Number of parameters:", sum(p.numel() for p in model.parameters()))