"""Benchmark every downloaded HF detector on data/images/<subset>/ -> models/benchmark.json
Run: .venv/Scripts/python scripts/benchmark_models.py"""
import glob, json, os, pathlib, torch
from PIL import Image
from sklearn.metrics import roc_auc_score, accuracy_score
from transformers import pipeline

FAKE_WORDS = ("fake", "artificial", "deepfake", "ai")

def p_fake(preds):
    """Normalise any label scheme to P(manipulated)."""
    return sum(p["score"] for p in preds if p["label"].lower().startswith(FAKE_WORDS) or p["label"].lower() in FAKE_WORDS)

subsets = {p.name: sorted(p.glob("*")) for p in pathlib.Path("data/images").iterdir() if p.is_dir()}
dev = 0 if torch.cuda.is_available() else -1
results = {}
for d in sorted(glob.glob("models/*/")):
    name = os.path.normpath(d).split(os.sep)[-1]
    clf = pipeline("image-classification", model=d, device=dev)
    scores = {s: [p_fake(clf(Image.open(f).convert("RGB"), top_k=None)) for f in files] for s, files in subsets.items()}
    real = scores.get("real", [])
    row = {}
    for s, sc in scores.items():
        if s == "real" or not real: continue
        y = [0] * len(real) + [1] * len(sc); x = real + sc
        row[s] = {"auc": round(roc_auc_score(y, x), 3), "acc@0.5": round(accuracy_score(y, [v > .5 for v in x]), 3)}
    row["fpr@0.5_on_real"] = round(sum(v > .5 for v in real) / max(len(real), 1), 3)
    results[name] = row
    print(name, json.dumps(row))
json.dump(results, open("models/benchmark.json", "w"), indent=2)
