# Veritas Lens — project context for coding agents (Claude Code / Antigravity)
Hackathon: deepEntra Build Fest 2026, challenge CYB-03 "Explainable Deepfake & Digital Identity Manipulation Detection".
Full strategy, judging weights, demo script: see PLAN.md. **Hard deadline: feature freeze 3:30 PM. Ship > perfect.**

## Challenge requirements (every one must be visibly satisfied in the UI)
1. Analyze image AND video samples for manipulation signals.
2. Report WHERE (frame + face region heatmap) and WHY (named signal + plain reason) content is suspicious.
3. Confidence (calibrated probability + band), failure cases, human review.
4. Evaluate on a real-vs-manipulated sample set; report accuracy, false positives and limits.
5. Guardrail: probabilistic only — never "fake", "proof", "guilty", "identity confirmed".

## Stack & layout
- Python 3.12 venv at `.venv` (run with `.venv/Scripts/python`), FastAPI + uvicorn, torch (CUDA if available, else CPU), transformers, mediapipe **tasks API** (`mediapipe.tasks.python.vision.FaceLandmarker`, model `models/face_landmarker.task`; the legacy `mp.solutions` API is NOT available in mediapipe 1.x), OpenCV, scikit-learn.
- Frontend: Vite + React + TypeScript + Tailwind + Recharts in `frontend/`. Proxy `/api` → `http://localhost:8000`.
```
backend/
  app.py              FastAPI routes, serves /static
  schemas.py          pydantic models = THE contract (mirror in frontend/src/types.ts)
  pipeline.py         analyze_image(path) / analyze_video(path) -> AnalysisResult
  face.py             detect face, crop (1.3x box), region masks from landmarks
  signals/
    classifier.py     S1 HF ensemble + occlusion heatmap
    ela.py            S2 error level analysis
    fft.py            S3 frequency spectrum
    noise.py          S4 noise residual face-vs-background
    metadata.py       S5 EXIF / software tags / C2PA presence
    temporal.py       V1 frame timeline, V2 blink rate, V3 landmark jitter
  fusion.py           logistic regression over signal scores (+ fallback fixed weights)
  narrator.py         LLM explanation from JSON only + template fallback
  store.py            SQLite: cases, reviews, audit log
  static/cases/<case_id>/*.png   generated heatmaps/panels
scripts/  eval.py (→ backend/static/metrics.json), benchmark_models.py, fetch_data.py, download_models.py
data/images/{real,faceswap,inpainting,text2img}/   data/videos/{real,fake}/   (local only, gitignored)
models/   HF detector folders + face_landmarker.task (local only, gitignored)
```

## Signal module contract (every signal is independent and pure)
```python
def run(img_rgb: np.ndarray, face: FaceInfo | None, case_dir: Path) -> Signal
# Signal(id, name, score: float 0..1 = suspicion, heatmap: str | None (url of saved png, same size as input),
#        reason: str (one sentence, concrete, measured), details: dict, ok: bool, error: str | None)
```
A signal that errors returns `ok=False` with the error. **The pipeline must never crash because one signal failed.**

## Models (all already in ./models, loaded once at startup, cached globally)
Label schemes differ. Always normalize to P(manipulated) = sum of scores whose label starts with fake/artificial/deepfake.
| folder | arch | labels | target |
|---|---|---|---|
| prithivMLmods__Deep-Fake-Detector-v2-Model | ViT | Realism / Deepfake | face deepfakes |
| dima806__deepfake_vs_real_image_detection | ViT | Real / Fake | face deepfakes |
| prithivMLmods__deepfake-detector-model-v1 | SigLIP | Fake / Real | face deepfakes |
| Organika__sdxl-detector | Swin | artificial / human | diffusion images |
| haywoodsloan__ai-image-detector-deploy | SwinV2 | artificial / real | AI-generated images |
| umm-maybe__AI-image-detector | Swin | artificial / human | AI-generated images |
Benchmark results per subset: `models/benchmark.json`.

### ⚠ Benchmark finding (measured 25 Sep, drives the S1 design)
Off-the-shelf classifiers are near-random on face-swap/inpainting (AUC 0.41–0.62); only AI-generated detectors work on text2img (haywoodsloan 0.93, Organika 0.87).
A **linear probe on frozen SigLIP embeddings of MediaPipe face crops** (backbone of `prithivMLmods__deepfake-detector-model-v1`, `model.vision_model(...).pooler_output`, StandardScaler + LogisticRegression C=0.1) reaches 5-fold CV AUC **0.83 face-swap / 0.90 inpainting / 0.92 text2img**; the same probe on the haywoodsloan SwinV2 backbone gets **0.87 / 0.88 / 0.95 (overall 0.90, FPR@0.5 19%)** with 239 real vs 238 fake faces (`scripts/probe_experiment.py`). Person D: also try concatenating both embeddings; keep whichever wins on the train split.
→ **S1 = probe score (primary) + haywoodsloan AI-generated score (secondary sub-score).** Probe is trained in `scripts/eval.py` on the train split only, saved to `models/probe.joblib`.
→ **Leakage guard:** all fakes are 512² while reals vary in size — ALWAYS face-crop (1.3× landmark box) and resize to 224 before any model. Never feed raw image size/format as a feature. State in limitations: "trained/evaluated on DeepFakeFace; real and fake images come from different sources, so part of the signal may be source/compression domain." Test on team selfies as an out-of-distribution check and show the result honestly.
→ Class imbalance: choose the operating threshold on the train split for FPR ≤ 10%, not 0.5.

## Signal specs
- **S1 classifier + occlusion:** SigLIP-embedding probe (see benchmark finding) on the 224² face crop (fallback: center crop). Heatmap = occlusion sensitivity: 7×7 grid, patch filled with image-mean color, heat = max(0, p_base − p_occluded), batch all 49 crops in one forward pass. Upsample, blur, colormap JET, alpha-blend 45% on the image.
- **S2 ELA:** re-save JPEG q=90, abs diff ×15, score = mean ELA inside face vs outside (ratio → sigmoid). Save ELA image.
- **S3 FFT:** grayscale face crop 256², log-magnitude spectrum, azimuthal average; score from high-frequency energy ratio + periodic peak count vs real baseline (calibrate constants on data/images/real). Save spectrum png.
- **S4 noise:** residual = img − medianBlur(img,3); compare residual std inside face mask vs background ring; large mismatch → splice/swap. Save residual heat.
- **S5 metadata:** EXIF presence, Software tag (photoshop/gimp/stable diffusion/midjourney…), missing camera make/model, C2PA/JUMBF marker bytes. Score low-weight; reasons are text only.
- **Regions:** from 478 landmarks build masks: left_eye, right_eye, mouth, nose, jaw_boundary (band along face oval, ±6% face width), skin (face oval minus features), background. Region suspicion = mean of S1 occlusion heat inside mask (normalized). Top region drives the headline: "Suspicion concentrated at jaw boundary — consistent with face-swap blending".
- **Video:** sample ≤16 frames evenly (cv2), per-frame S1 score → timeline; top-3 frames get full heatmaps; blink rate via eye aspect ratio on landmarks (human ≈ 15–20/min; <5 flagged as weak indicator); landmark jitter = mean frame-to-frame landmark displacement normalized by face size. Video fused score = 0.6·mean(top-25% frames) + 0.4·temporal.
- **Robustness:** re-run S1 after JPEG q=50 and 50% downscale; report the scores (shows stability, feeds `limitations`).
- **Limitations list (auto):** face < 128 px, no face found, multiple faces, heavy compression (JPEG q estimate < 60), side profile (yaw large), video < 1 s, signals disagree strongly.

## Output bands & wording (use EXACTLY)
- `< 0.35` clean → "No strong manipulation indicators found"
- `0.35–0.70` inconclusive → "Inconclusive — human review required"
- `> 0.70` strong → "Strong manipulation indicators — human review required"
- Disclaimer on every result/report: "Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer."

## API (contract; frontend mocks from `frontend/src/mock.json` until backend is live)
- `POST /api/analyze` multipart `file` → AnalysisResult (see PLAN.md §2 for JSON shape)
- `GET /api/cases` · `GET /api/cases/{id}` · `POST /api/cases/{id}/review {decision: agree|disagree|needs_more, note}`
- `GET /api/metrics` → metrics.json · `GET /api/cases/{id}/report` → printable HTML
- `GET /api/health` → models loaded, device

## Frontend screens
1. **Analyze** — drag-drop, sample gallery (hero samples one-click), progress steps.
2. **Evidence report** — band banner + gauge, original vs heatmap slider/opacity, region chips ranked, signal cards (score bar, reason, panel image), contribution bars, video frame timeline (click frame → its heatmap), narrator text, limitations, SHA-256, disclaimer, "Send to review", Print.
3. **Evaluation** — accuracy, precision, recall, FPR, AUC tiles; ROC curve; confusion matrix; per-subset table; robustness table; fusion vs single-signal; failure gallery with reasons.
4. **Review queue** — cases table, decision buttons, notes, audit log.
Design: dark, forensic-lab feel, teal accent (#14b8a6, matches CYB domain color), clean typography, no clutter.

## Conventions
- Keep functions small; type hints; no notebooks. Log timings per signal.
- Never block startup on network. All models load from ./models (`local_files_only=True`).
- Commit small and often to your own branch; merge to `main` at checkpoints (1:45, 2:45, 3:15).
