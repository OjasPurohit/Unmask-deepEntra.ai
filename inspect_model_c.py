import torch
from huggingface_hub import hf_hub_download

MODEL_NAME = "Arko007/deepfake-image-detector"

checkpoint_path = hf_hub_download(
    repo_id=MODEL_NAME,
    filename="pytorch_model.bin"
)

checkpoint = torch.load(
    checkpoint_path,
    map_location="cpu"
)

if "state_dict" in checkpoint:
    checkpoint = checkpoint["state_dict"]

print("\n===================================")
print(" Model C Checkpoint Structure")
print("===================================\n")

for key, value in checkpoint.items():

    if key.startswith("classifier."):

        print(
            f"{key:45} {tuple(value.shape)}"
        )

print("\n===================================")