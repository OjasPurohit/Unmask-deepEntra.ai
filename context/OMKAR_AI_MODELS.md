# Context: AI MODELS — Omkar · Unmask (CYB-03)
> Paste into Antigravity as context (or @-mention this file). Also read ../CLAUDE.md and ../PLAN.md.
> Branch: **`models`**. Merge into `main` at 1:45 / 2:45 / 3:15.

## Your mission in one line
Own the **detection core and the numbers**: find the face, run S1 (`cf` + `probe`) with its occlusion heatmap and region attribution, fuse every signal into one calibrated confidence, and produce the evaluation report (accuracy, false positives, per-subset results, robustness, failure cases). This is the "where and why" plus the 25% "technical execution" score.

## What is already true (measured 25 Sep, don't redo)
- The downloaded detectors **fail on face swaps and inpainting** (AUC 0.41–0.62, coin-flip level). Results: `models/benchmark.json`, script: `scripts/benchmark_models.py`.
- **What works:** a linear probe on frozen embeddings of **MediaPipe face crops**. `scripts/probe_experiment.py`, 5-fold CV on 239 real / 238 fake faces:

| backbone (in ./models) | overall AUC | face swap | inpainting | text2img | FPR @0.5 |
|---|---|---|---|---|---|
| haywoodsloan__ai-image-detector-deploy (SwinV2) | **0.904** | **0.867** | 0.880 | **0.953** | 19% |
| prithivMLmods__deepfake-detector-model-v1 (SigLIP, `.vision_model`) | 0.886 | 0.825 | **0.904** | 0.920 | 19% |
| dima806__deepfake_vs_real_image_detection (ViT) | 0.864 | 0.850 | 0.811 | 0.916 | 20% |

### Update 26 Sep: Omkar's model is the strongest single detector
`buildborderless/CommunityForensics-DeepfakeDet-ViT` (in `models/`, one sigmoid output = P(manipulated)): AUC **faceswap 0.66 · inpainting 0.99 · text2img 1.00 · FPR@0.5 = 0.3%**. It is weak exactly where the probe is strong (face swaps). **Use both as separate features in fusion**, and report `cf`, `probe` and `fused` AUCs side by side in `per_signal_auc`: that table is our proof that combining signals helps.

## Data (local only, gitignored; get it from the pen drive or run `scripts/fetch_data.py`)
- `data/images/real` (350, Wikipedia portraits, varied sizes), `faceswap` / `inpainting` / `text2img` (100 each, all 512×512). Source: OpenRL/DeepFakeFace.
- Videos are **out of scope** (image-only KYC). Ignore `data/videos/`.
- MediaPipe finds faces in ~70% of images; images with no face are reported as "no face found" (a limitation), not silently dropped from the counts.

## ⚠ Leakage guard (judges may ask, so be ready to answer)
Fakes are all 512², reals vary. **Always face-crop (1.3× landmark box) → resize 224 before any model.** Never use size/format as a feature. Write in the limitations: *"Real and manipulated samples come from different sources; part of the learned signal may reflect source/compression rather than manipulation. Out-of-distribution check: team selfies."* Run the team selfies through the system and show the result, whatever it is.

## Your build tasks, in order (P0 → P1)
### P0a — the detection core (this is new: `face.py` and `classifier.py` are yours)
1. **`backend/face.py`** — MediaPipe **tasks** API `FaceLandmarker` (`models/face_landmarker.task`, IMAGE mode; the legacy `mp.solutions` API does not exist in mediapipe 1.x). Return
   `FaceInfo(box, crop_rgb (1.3× landmark box, resized 224), landmarks 478×2 px, masks: dict[str, bool array], yaw)`
   with masks for `left_eye, right_eye, mouth, nose, jaw_boundary` (band along the face oval, ±6% face width), `skin` (oval minus features) and `background`. Build them from the FACEMESH index sets of the landmark topology. Fallback if no landmarks: OpenCV Haar box + proportional regions, and flag it as a limitation.
2. **`backend/signals/classifier.py` (S1, two sub-scores — see CLAUDE.md "Signal specs")**
   - `cf` = `buildborderless__CommunityForensics-DeepfakeDet-ViT` on the **full image**, `function_to_apply="sigmoid"`; the single output already IS P(manipulated). No crop.
   - `probe` = `models/probe.joblib` on the frozen **haywoodsloan SwinV2 backbone** embedding of the 224² face crop (switch to SigLIP or the two concatenated only if that wins on the train split, task 5).
   - Put both in `Signal.details` as `{"cf": …, "probe": …}`; they enter fusion as **two separate features**. The score shown in the UI is `max(cf, probe)`.
   - **Occlusion heatmap** on whichever sub-score is higher: 7×7 grid, patch filled with the image-mean color, heat = `max(0, p_base − p_occluded)`, all 49 crops batched in **one** forward pass. Upsample, blur, JET colormap, alpha-blend 45%. Save the overlay png.
   - Also expose `predict_batch(list[img]) -> list[float]` — your robustness run and eval.py call it.
   - Load every model once at startup, `local_files_only=True`, GPU if available. Target < 2 s/image on GPU, < 8 s on CPU.
3. **`region_scores(heat, masks) -> list[RegionScore]` + headline** — region suspicion = normalized mean occlusion heat inside each mask, sorted. Top region drives the headline sentence, e.g. *"Suspicion concentrated at jaw boundary — consistent with face-swap blending"*. This one sentence is the centrepiece of the demo; make it read well.

### P0b — the numbers
4. **Cache embeddings** → `scripts/embed.py`: face-crop every image once, save `data/cache/{backbone}.npz` (X, y, subset, path). Reuse the crop logic from `scripts/probe_experiment.py`.

5. **Train the probe** (`scripts/train_probe.py`): fixed stratified 70/30 split (seed 7, saved to `data/cache/split.json`). Try SwinV2, SigLIP, and both concatenated; pick the best by train-split CV AUC. Save `models/probe.joblib` = {backbone, scaler+LR pipeline, threshold}. Pick the threshold on the train split so **FPR ≤ 10%**.
6. **`scripts/eval.py`** → `backend/static/metrics.json` (the frontend renders this file; keep exactly these keys):
```json
{
  "dataset": {"real": 239, "manipulated": 238, "subsets": ["faceswap","inpainting","text2img"], "source": "OpenRL/DeepFakeFace", "test_split": 0.3},
  "threshold": 0.62,
  "overall": {"accuracy":0.85,"precision":0.84,"recall":0.81,"fpr":0.09,"fnr":0.19,"auc":0.90},
  "confusion": {"tp":58,"fp":6,"tn":66,"fn":13},
  "roc": [{"fpr":0.0,"tpr":0.0}, {"fpr":0.1,"tpr":0.72}],
  "per_subset": [{"subset":"faceswap","auc":0.87,"recall":0.78,"n":22}],
  "per_signal_auc": [{"signal":"cf","auc":0.88},{"signal":"probe","auc":0.90},{"signal":"ela","auc":0.61},{"signal":"fused","auc":0.93}],
  "robustness": [{"condition":"original","auc":0.90},{"condition":"jpeg_q50","auc":0.84},{"condition":"resize_50","auc":0.80}],
  "failures": [{"path":"/static/failures/f1.jpg","label":"real","score":0.81,"reason":"Heavy JPEG compression and low-resolution face (<128 px)"}],
  "ood_check": {"name":"team selfies","n":8,"flagged":1},
  "limitations": ["..."]
}
```
7. **`backend/fusion.py`**: LogisticRegression over signal scores `[cf, probe, ela, fft, noise, metadata]` (S1 contributes **two** features), fit on the train split. `fuse(scores) -> (prob, contributions{signal: coef*x})`. If `models/fusion.json` is missing, fall back to fixed weights. Bands: <0.35 clean, 0.35–0.70 inconclusive, >0.70 strong.
8. **Robustness**: re-embed the test split after JPEG q=50 and 50% downscale → AUC per condition.
9. **Failure gallery**: the 6 worst test errors, copied to `backend/static/failures/`, each with an auto-generated reason (small face, low JPEG quality, profile pose, signals disagree).
10. **Hero samples**: copy 2 real, 2 face-swap, 1 inpainting, 1 text2img, 1 known failure into `backend/static/samples/` for the demo.

## Interfaces you depend on / provide
- **You depend on:** `backend/schemas.py` (Ojas) for `Signal`/`RegionScore`, and Yadnesh's `backend/signals/{ela,fft,noise,metadataal}.py` — same `run(img_rgb, face, case_dir) -> Signal` contract. Until they merge, fuse `cf` + `probe` alone.
- **You provide:** `backend/face.py` (`detect(img) -> FaceInfo | None`), `backend/signals/classifier.py` (`run(...)`, `predict_batch(imgs) -> list[float]`, `region_scores(heat, masks)`), `backend/fusion.py`, `models/probe.joblib`, `models/fusion.json`, `backend/static/metrics.json`. Yadnesh stubs `face.detect` and `classifier.predict_batch` until you merge — keep those two signatures stable.

## Files you own (nobody else edits them)
`backend/face.py` · `backend/signals/classifier.py` · `backend/fusion.py` · `scripts/embed.py`, `train_probe.py`, `eval.py`, `probe_experiment.py`, `benchmark_models.py` · `models/probe.joblib`, `models/fusion.json` · `backend/static/metrics.json`.

## Checkpoints
**1:45** `face.py` + `classifier.py` live (cf + probe + occlusion heatmap + regions) and probe trained, metrics.json v1 (S1 only) · **2:45** fusion over all signals + robustness + failure gallery · **3:15** final metrics.json frozen. **Never overwrite metrics.json with a broken run**: write to a temp file, then rename it.
