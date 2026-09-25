"""Download detector models + MediaPipe face model into ./models (≈5 GB total; set MODELS=... to limit).
Run: .venv/Scripts/python scripts/download_models.py"""
import os, urllib.request
from huggingface_hub import snapshot_download

MODELS = os.environ.get("MODELS", ",".join([
    "prithivMLmods/Deep-Fake-Detector-v2-Model",   # ViT, deepfake faces
    "dima806/deepfake_vs_real_image_detection",    # ViT, deepfake faces
    "prithivMLmods/deepfake-detector-model-v1",    # SigLIP, deepfake faces
    "Organika/sdxl-detector",                      # Swin, AI-generated (diffusion)
    "haywoodsloan/ai-image-detector-deploy",       # SwinV2, AI-generated
    "umm-maybe/AI-image-detector",                 # Swin, AI-generated
    "buildborderless/CommunityForensics-DeepfakeDet-ViT",  # ViT, single sigmoid output; best on generated/inpainted
])).split(",")
for m in MODELS:
    print("->", m)
    snapshot_download(m, local_dir=f"models/{m.replace('/', '__')}",
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"] if "umm-maybe" not in m else ["*.json", "*.bin", "*.txt"])
url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
if not os.path.exists("models/face_landmarker.task"):
    urllib.request.urlretrieve(url, "models/face_landmarker.task")
print("models ready")
