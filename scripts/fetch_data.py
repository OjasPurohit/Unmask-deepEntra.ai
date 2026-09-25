"""Fetch a small labelled eval set. Run: .venv/Scripts/python scripts/fetch_data.py"""
import json, random, os, pathlib
from remotezip import RemoteZip
from huggingface_hub import hf_hub_url, hf_hub_download, HfApi
random.seed(7)
N = int(os.environ.get("N_PER_CLASS", 100))
ROOT = pathlib.Path("data/images")
# DeepFakeFace: wiki=real, insight=face-swap (InsightFace), inpainting=SD inpaint, text2img=SD generated
SUBSETS = os.environ.get("SUBSETS", "real,faceswap,inpainting,text2img").split(",")
for z, label, subset in [("wiki.zip","real","real"),("insight.zip","fake","faceswap"),("inpainting.zip","fake","inpainting"),("text2img.zip","fake","text2img")]:
    if subset not in SUBSETS: continue
    out = ROOT/subset; out.mkdir(parents=True, exist_ok=True)
    if len(list(out.glob("*"))) >= N: print("skip", subset); continue
    with RemoteZip(hf_hub_url("OpenRL/DeepFakeFace", z, repo_type="dataset")) as rz:
        names = [n for n in rz.namelist() if n.lower().endswith((".jpg",".jpeg",".png"))]
        for n in random.sample(names, min(N, len(names))):
            (out/(n.replace("/","_"))).write_bytes(rz.read(n))
    print("done", subset, len(list(out.glob('*'))))
# DFDC sample videos with labels from metadata.json
if os.environ.get("SKIP_VIDEOS"): raise SystemExit
V = pathlib.Path("data/videos"); V.mkdir(parents=True, exist_ok=True)
repo = "191fa07121/deepfake-detection-challenge"
files = [f for f in HfApi().list_repo_files(repo, repo_type="dataset")]
meta = [f for f in files if f.endswith("metadata.json")]
labels = json.load(open(hf_hub_download(repo, meta[0], repo_type="dataset"))) if meta else {}
real = [k for k,v in labels.items() if v.get("label")=="REAL" and k in files]
fake = [k for k,v in labels.items() if v.get("label")=="FAKE" and k in files]
NV = int(os.environ.get("N_VIDEOS", 10))
pick = {k:"real" for k in random.sample(real, min(NV,len(real)))} | {k:"fake" for k in random.sample(fake, min(NV,len(fake)))}
for k, lab in pick.items():
    p = hf_hub_download(repo, k, repo_type="dataset", local_dir=V/"_dl")
    d = V/lab; d.mkdir(exist_ok=True); os.replace(p, d/k)
print("videos", {l: len(list((V/l).glob('*.mp4'))) for l in ["real","fake"]}, "metadata found:", bool(meta))
