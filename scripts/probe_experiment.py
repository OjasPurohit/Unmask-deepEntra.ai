"""Research: linear probe on frozen embeddings of MediaPipe face crops (leakage-safe). 5-fold CV AUC per subset."""
import pathlib, numpy as np, torch, mediapipe as mp
from PIL import Image
from mediapipe.tasks.python import vision, BaseOptions
from transformers import AutoModel, AutoImageProcessor
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path="models/face_landmarker.task"), num_faces=1))
def crop(p):
    im = np.array(Image.open(p).convert("RGB")); r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=im))
    if not r.face_landmarks: return None
    h, w = im.shape[:2]; xs = [l.x * w for l in r.face_landmarks[0]]; ys = [l.y * h for l in r.face_landmarks[0]]
    cx, cy, s = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, max(max(xs)-min(xs), max(ys)-min(ys)) * 1.3 / 2
    return Image.fromarray(im).crop((int(cx-s), int(cy-s), int(cx+s), int(cy+s))).resize((224, 224))
items = [(c, s) for s in ["real","faceswap","inpainting","text2img"] for p in sorted(pathlib.Path("data/images", s).glob("*")) if (c := crop(p)) is not None]
print("faces found:", {s: sum(1 for _, t in items if t == s) for s in ["real","faceswap","inpainting","text2img"]})
subs = np.array([s for _, s in items])
for name in ["prithivMLmods__deepfake-detector-model-v1", "haywoodsloan__ai-image-detector-deploy", "dima806__deepfake_vs_real_image_detection"]:
    proc = AutoImageProcessor.from_pretrained(f"models/{name}"); m = AutoModel.from_pretrained(f"models/{name}").cuda().eval()
    feats = []
    with torch.no_grad():
        for i in range(0, len(items), 32):
            x = proc(images=[c for c, _ in items[i:i+32]], return_tensors="pt")["pixel_values"].cuda()
            o = m.vision_model(pixel_values=x) if hasattr(m, "vision_model") else m(pixel_values=x)
            f = o.pooler_output if getattr(o, "pooler_output", None) is not None else o.last_hidden_state.mean(1)
            feats.append(f.float().cpu().numpy())
    X = np.concatenate(feats); y = (subs != "real").astype(int)
    p = cross_val_predict(make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000)), X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")[:, 1]
    per = {s: round(roc_auc_score(y[(subs == "real") | (subs == s)], p[(subs == "real") | (subs == s)]), 3) for s in ["faceswap","inpainting","text2img"]}
    print(name, "overall AUC", round(roc_auc_score(y, p), 3), per, "FPR@0.5", round(((p > .5) & (y == 0)).sum() / (y == 0).sum(), 3))
