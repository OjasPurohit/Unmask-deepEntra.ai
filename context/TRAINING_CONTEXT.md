# Context: TRAINING / EVALUATION owner — Veritas Lens (CYB-03)
> Paste into Antigravity as context (or @-mention this file). Also read ../CLAUDE.md and ../PLAN.md.

## Your mission in one line
Own the **numbers**: train the detector probe, fuse all signals into one calibrated confidence score, and produce the evaluation report (accuracy, false positives, per-subset results, robustness, failure cases). Evaluation is an explicit challenge requirement, and a big part of the 25% "technical execution" score.

## What is already true (measured 25 Sep, don't redo)
- The downloaded detectors **fail on face swaps and inpainting** (AUC 0.41–0.62, coin-flip level). Results: `models/benchmark.json`, script: `scripts/benchmark_models.py`.
- **What works:** a linear probe on frozen embeddings of **MediaPipe face crops**. `scripts/probe_experiment.py`, 5-fold CV on 239 real / 238 fake faces:

| backbone (in ./models) | overall AUC | face swap | inpainting | text2img | FPR @0.5 |
|---|---|---|---|---|---|
| haywoodsloan__ai-image-detector-deploy (SwinV2) | **0.904** | **0.867** | 0.880 | **0.953** | 19% |
| prithivMLmods__deepfake-detector-model-v1 (SigLIP, `.vision_model`) | 0.886 | 0.825 | **0.904** | 0.920 | 19% |
| dima806__deepfake_vs_real_image_detection (ViT) | 0.864 | 0.850 | 0.811 | 0.916 | 20% |

## Data (local only, gitignored; get it from the pen drive or run `scripts/fetch_data.py`)
- `data/images/real` (350, Wikipedia portraits, varied sizes), `faceswap` / `inpainting` / `text2img` (100 each, all 512×512). Source: OpenRL/DeepFakeFace.
- `data/videos/real`, `data/videos/fake` (10 each, DFDC sample).
- MediaPipe finds faces in ~70% of images; images with no face are reported as "no face found" (a limitation), not silently dropped from the counts.

## ⚠ Leakage guard (judges may ask, so be ready to answer)
Fakes are all 512², reals vary. **Always face-crop (1.3× landmark box) → resize 224 before any model.** Never use size/format as a feature. Write in the limitations: *"Real and manipulated samples come from different sources; part of the learned signal may reflect source/compression rather than manipulation. Out-of-distribution check: team selfies."* Run the team selfies through the system and show the result, whatever it is.

## Your build tasks, in order (P0 → P1)
1. **Cache embeddings** → `scripts/embed.py`: face-crop every image once, save `data/cache/{backbone}.npz` (X, y, subset, path). Reuse the crop logic from `scripts/probe_experiment.py`.
2. **Train the probe** (`scripts/train_probe.py`): fixed stratified 70/30 split (seed 7, saved to `data/cache/split.json`). Try SwinV2, SigLIP, and both concatenated; pick the best by train-split CV AUC. Save `models/probe.joblib` = {backbone, scaler+LR pipeline, threshold}. Pick the threshold on the train split so **FPR ≤ 10%**.
3. **`scripts/eval.py`** → `backend/static/metrics.json` (the frontend renders this file; keep exactly these keys):
```json
{
  "dataset": {"real": 239, "manipulated": 238, "subsets": ["faceswap","inpainting","text2img"], "source": "OpenRL/DeepFakeFace", "test_split": 0.3},
  "threshold": 0.62,
  "overall": {"accuracy":0.85,"precision":0.84,"recall":0.81,"fpr":0.09,"fnr":0.19,"auc":0.90},
  "confusion": {"tp":58,"fp":6,"tn":66,"fn":13},
  "roc": [{"fpr":0.0,"tpr":0.0}, {"fpr":0.1,"tpr":0.72}],
  "per_subset": [{"subset":"faceswap","auc":0.87,"recall":0.78,"n":22}],
  "per_signal_auc": [{"signal":"classifier","auc":0.90},{"signal":"ela","auc":0.61},{"signal":"fused","auc":0.92}],
  "robustness": [{"condition":"original","auc":0.90},{"condition":"jpeg_q50","auc":0.84},{"condition":"resize_50","auc":0.80}],
  "video": {"n":20,"accuracy":0.7,"auc":0.75},
  "failures": [{"path":"/static/failures/f1.jpg","label":"real","score":0.81,"reason":"Heavy JPEG compression and low-resolution face (<128 px)"}],
  "ood_check": {"name":"team selfies","n":8,"flagged":1},
  "limitations": ["..."]
}
```
4. **`backend/fusion.py`**: LogisticRegression over signal scores `[classifier, ela, fft, noise, metadata]`, fit on the train split. `fuse(scores) -> (prob, contributions{signal: coef*x})`. If `models/fusion.json` is missing, fall back to fixed weights. Bands: <0.35 clean, 0.35–0.70 inconclusive, >0.70 strong.
5. **Robustness**: re-embed the test split after JPEG q=50 and 50% downscale → AUC per condition.
6. **Failure gallery**: the 6 worst test errors, copied to `backend/static/failures/`, each with an auto-generated reason (small face, low JPEG quality, profile pose, signals disagree).
7. **Hero samples**: copy 2 real, 2 face-swap, 1 inpainting, 1 text2img, 1 fake video and 1 known failure into `backend/static/samples/` for the demo.

## Interfaces you depend on / provide
- The signals (ELA/FFT/noise/metadata) come from the backend person's modules: `run(img_rgb, face, case_dir) -> Signal` with `.score` 0–1. Until they're merged, fuse the classifier score alone.
- You provide: `models/probe.joblib`, `models/fusion.json`, `backend/static/metrics.json`, and `classifier.predict_face(crop_224) -> float` if the backend person asks.

## Checkpoints
1:45 probe trained + metrics.json v1 (classifier only) · 2:45 fusion + robustness + failures · 3:15 final metrics.json frozen. **Never overwrite metrics.json with a broken run**: write to a temp file, then rename it.
