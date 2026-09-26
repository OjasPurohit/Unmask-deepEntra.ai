# Unmask — project context for coding agents (Claude Code / Antigravity)
Hackathon: deepEntra Build Fest 2026, challenge CYB-03 "Explainable Deepfake & Digital Identity Manipulation Detection".
Full strategy, judging weights, demo script: see PLAN.md. **Hard deadline: feature freeze 3:30 PM. Ship > perfect.**

> ## ⚠ SCOPE LOCK (26 Sep, set by Ojas, overrides anything below)
> **Unmask is IMAGE-ONLY, for KYC identity verification.** Input = a KYC selfie, ID-card photo or ID portrait. Output = manipulation screening + **face heatmap** + **KYC evidence report** (on screen + printable PDF).
> - **NO video anywhere**: no `temporal.py`, no frame sampling, no blink/jitter, no `frames`/`temporal` fields, no video upload, no DFDC videos in eval. Ignore any leftover video mention in older docs.
> - **Use case:** a KYC/onboarding desk (VSS admissions, banks, fintech onboarding) screens submitted identity photos for face swaps, AI-generated faces and edited/inpainted faces before a human approves.
> - **ID-card scans:** the face on a card is small. `face.py` detects it and crops it (1.3x box); if the face is under 128 px, say so in limitations. The heatmap is drawn on the full uploaded image, focused on the face region.
> - Upload accepts `image/*` only (jpg, png, webp). `media_type` is always `"image"`.

## Challenge requirements (every one must be visibly satisfied in the UI)
1. Analyze KYC identity **images** (selfies, ID-card photos, ID portraits) for manipulation signals. Image-only: no video.
2. Report WHERE (face-region heatmap on the image) and WHY (named signal + plain reason) content is suspicious, in an on-screen + printable **KYC evidence report**.
3. Confidence (calibrated probability + band), failure cases, human review.
4. Evaluate on a real-vs-manipulated sample set; report accuracy, false positives and limits.
5. Guardrail: probabilistic only — never "fake", "proof", "guilty", "identity confirmed".

## Stack & layout
- Python 3.12 venv at `.venv` (run with `.venv/Scripts/python`), FastAPI + uvicorn, torch (CUDA if available, else CPU), transformers, mediapipe **tasks API** (`mediapipe.tasks.python.vision.FaceLandmarker`, model `models/face_landmarker.task`; the legacy `mp.solutions` API is NOT available in mediapipe 1.x), OpenCV, scikit-learn.
- Frontend: Vite + React + TypeScript + Tailwind + Recharts in `frontend/`. Proxy `/api` → `http://localhost:8000`.
- Android: **Capacitor** wraps the SAME React build into an APK (appId `ai.unmask.app`, webDir `dist`). No separate native codebase; the phone is a thin client calling the FastAPI backend over LAN. Spec: `context/ANDROID_APP.md`.
```
backend/
  app.py              FastAPI routes, serves /static
  schemas.py          pydantic models = THE contract (mirror in frontend/src/types.ts)
  pipeline.py         analyze_image(path) -> AnalysisResult   (image-only)
  face.py             detect face, crop (1.3x box), region masks from landmarks
  signals/
    classifier.py     S1 cf (CommunityForensics, full image) + probe (face-crop embedding) + occlusion heatmap
    ela.py            S2 error level analysis
    fft.py            S3 frequency spectrum
    noise.py          S4 noise residual face-vs-background
    metadata.py       S5 EXIF / software tags / C2PA presence
  report.py           KYC evidence report: printable HTML for GET /api/cases/{id}/report (Yadnesh)
  fusion.py           logistic regression over [cf, probe, ela, fft, noise, metadata] (+ fallback fixed weights)
  narrator.py         LLM explanation from JSON only + template fallback
  store.py            SQLite: cases, reviews, audit log
  static/cases/<case_id>/*.png   generated heatmaps/panels
frontend/                Vite + React app (web AND the Android webview build)
  android/               Capacitor-generated Android project (created by `npx cap add android`)
  capacitor.config.ts    appId ai.unmask.app, webDir dist, server.cleartext true
context/  OMKAR_AI_MODELS.md · YADNESH_BACKEND.md · FRONTEND_OJAS_PALASH.md · ANDROID_APP.md
scripts/  eval.py (→ backend/static/metrics.json), calibrate_signals.py, benchmark_models.py, fetch_data.py, download_models.py
data/images/{real,faceswap,inpainting,text2img}/   (local only, gitignored; data/videos is NOT used)
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
**Exception:** `buildborderless__CommunityForensics-DeepfakeDet-ViT` has ONE sigmoid output that already IS P(manipulated) — load it with `function_to_apply="sigmoid"` and feed it the **full image** (no face crop).
| folder | arch | labels | target |
|---|---|---|---|
| prithivMLmods__Deep-Fake-Detector-v2-Model | ViT | Realism / Deepfake | face deepfakes |
| dima806__deepfake_vs_real_image_detection | ViT | Real / Fake | face deepfakes |
| prithivMLmods__deepfake-detector-model-v1 | SigLIP | Fake / Real | face deepfakes |
| Organika__sdxl-detector | Swin | artificial / human | diffusion images |
| haywoodsloan__ai-image-detector-deploy | SwinV2 | artificial / real | AI-generated images |
| umm-maybe__AI-image-detector | Swin | artificial / human | AI-generated images |
| buildborderless__CommunityForensics-DeepfakeDet-ViT | ViT | single sigmoid output = P(manipulated) | generated + inpainted faces (full image) |
Benchmark results per subset: `models/benchmark.json`.

### ⚠ Benchmark finding (measured 25 Sep, drives the S1 design)
Off-the-shelf classifiers are near-random on face-swap/inpainting (AUC 0.41–0.62); only AI-generated detectors work on text2img (haywoodsloan 0.93, Organika 0.87).
A **linear probe on frozen SigLIP embeddings of MediaPipe face crops** (backbone of `prithivMLmods__deepfake-detector-model-v1`, `model.vision_model(...).pooler_output`, StandardScaler + LogisticRegression C=0.1) reaches 5-fold CV AUC **0.83 face-swap / 0.90 inpainting / 0.92 text2img**; the same probe on the haywoodsloan SwinV2 backbone gets **0.87 / 0.88 / 0.95 (overall 0.90, FPR@0.5 19%)** with 239 real vs 238 fake faces (`scripts/probe_experiment.py`). Omkar: also try concatenating both embeddings; keep whichever wins on the train split.
**Update 26 Sep (Omkar's find):** `buildborderless/CommunityForensics-DeepfakeDet-ViT` (single sigmoid output = P(manipulated), use `function_to_apply="sigmoid"`) scores AUC **0.66 face-swap / 0.99 inpainting / 1.00 text2img with only 0.3% false positives** on real images (full image, no crop needed).
→ **S1 = two sub-scores: `cf` (CommunityForensics, catches generated/inpainted) + `probe` (face-crop embedding probe, catches face swaps).** Both go into fusion as separate features. Probe is trained in `scripts/eval.py` on the train split only, saved to `models/probe.joblib`.
→ **Leakage guard:** all fakes are 512² while reals vary in size — ALWAYS face-crop (1.3× landmark box) and resize to 224 before any model. Never feed raw image size/format as a feature. State in limitations: "trained/evaluated on DeepFakeFace; real and fake images come from different sources, so part of the signal may be source/compression domain." Test on team selfies as an out-of-distribution check and show the result honestly.
→ Class imbalance: choose the operating threshold on the train split for FPR ≤ 10%, not 0.5.

## Signal specs
- **S1 classifier + occlusion (two sub-scores):**
  - `cf` — `buildborderless__CommunityForensics-DeepfakeDet-ViT` on the **full image** (no crop), `function_to_apply="sigmoid"`; the single sigmoid output IS P(manipulated). Catches generated and inpainted content.
  - `probe` — linear probe (StandardScaler + LogisticRegression C=0.1, `models/probe.joblib`) on the frozen **haywoodsloan SwinV2 backbone embedding** of the 224² MediaPipe face crop (1.3× landmark box; fallback: center crop). Catches face swaps. Only switch the backbone to SigLIP (`prithivMLmods__deepfake-detector-model-v1`, `.vision_model(...).pooler_output`) or to the two embeddings concatenated **if that wins on the train split**.
  - Both sub-scores go in `Signal.details` (`{"cf": …, "probe": …}`) and into fusion as **two separate features**. The S1 score shown in the UI = `max(cf, probe)`.
  - Heatmap = occlusion sensitivity on **whichever sub-score is higher**: 7×7 grid, patch filled with image-mean color, heat = max(0, p_base − p_occluded), batch all 49 crops in one forward pass. Upsample, blur, colormap JET, alpha-blend 45% on the image. (`cf` occludes the full image, `probe` occludes the face crop.)
- **S2 ELA:** re-save JPEG q=90, abs diff ×15, score = mean ELA inside face vs outside (ratio → sigmoid). Save ELA image.
- **S3 FFT:** grayscale face crop 256², log-magnitude spectrum, azimuthal average; score from high-frequency energy ratio + periodic peak count vs real baseline (calibrate constants on data/images/real). Save spectrum png.
- **S4 noise:** residual = img − medianBlur(img,3); compare residual std inside face mask vs background ring; large mismatch → splice/swap. Save residual heat.
- **S5 metadata:** EXIF presence, Software tag (photoshop/gimp/stable diffusion/midjourney…), missing camera make/model, C2PA/JUMBF marker bytes. Score low-weight; reasons are text only.
- **Regions:** from 478 landmarks build masks: left_eye, right_eye, mouth, nose, jaw_boundary (band along face oval, ±6% face width), skin (face oval minus features), background. Region suspicion = mean of S1 occlusion heat inside mask (normalized). Top region drives the headline: "Suspicion concentrated at jaw boundary — consistent with face-swap blending".
- **Robustness:** re-run S1 after JPEG q=50 and 50% downscale; report the scores (shows stability, feeds `limitations`).
- **Limitations list (auto):** face < 128 px (common on ID-card scans), no face found, multiple faces, heavy compression (JPEG q estimate < 60), side profile (yaw large), signals disagree strongly.

## Output bands & wording (use EXACTLY)
- `< 0.35` clean → "No strong manipulation indicators found"
- `0.35–0.70` inconclusive → "Inconclusive — human review required"
- `> 0.70` strong → "Strong manipulation indicators — human review required"
- Disclaimer on every result/report: "Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer."

## API (contract; frontend mocks from `frontend/src/mock.json` until backend is live)
**Authoritative field list = the `types.ts` block in `context/FRONTEND_OJAS_PALASH.md`; `backend/schemas.py` must mirror it. metrics.json shape = `context/OMKAR_AI_MODELS.md` step 3.**
- `POST /api/analyze` multipart `file` → AnalysisResult (see PLAN.md §2 for JSON shape)
- `GET /api/cases` · `GET /api/cases/{id}` · `POST /api/cases/{id}/review {decision: agree|disagree|needs_more, note}`
- `GET /api/metrics` → metrics.json · `GET /api/cases/{id}/report` → printable HTML
- `GET /api/health` → models loaded, device
- **Android/LAN:** CORS `allow_origins=["*"]`, run uvicorn with `--host 0.0.0.0`, open Windows firewall TCP 8000. Every image/static path in a response is returned as a root-relative URL (`/static/...`) so the phone client can prefix its own backend base URL.

## Frontend screens
All screens must be usable at **390 px width** (the Android app is the same build). API base URL comes from `VITE_API_BASE` (default `""` → Vite proxy on web; `http://<laptop-LAN-IP>:8000` for the APK), and every image/static URL is built through one helper that prefixes it. A Settings field (saved in `localStorage`) changes the backend URL at runtime. Upload input: `accept="image/*"` plus `capture` so the phone camera opens directly. See `context/ANDROID_APP.md`.
1. **Analyze** — drag-drop, sample gallery (hero samples one-click), progress steps.
2. **Evidence report (the KYC report)** — band banner + gauge, original vs heatmap slider/opacity, region chips ranked, signal cards (score bar, reason, panel image), contribution bars, narrator text, limitations, SHA-256, disclaimer, "Send to review", Print → PDF. Titled "KYC Verification Evidence Report".
3. **Evaluation** — accuracy, precision, recall, FPR, AUC tiles; ROC curve; confusion matrix; per-subset table; robustness table; fusion vs single-signal; failure gallery with reasons.
4. **Review queue** — cases table, decision buttons, notes, audit log.
Design: dark, forensic-lab feel, teal accent (#14b8a6, matches CYB domain color), clean typography, no clutter.

## Conventions
- Keep functions small; type hints; no notebooks. Log timings per signal.
- Never block startup on network. All models load from ./models (`local_files_only=True`).
- Branches: `main` (Ojas, scaffold + merges) · `ui` (Palash) · `models` (Omkar) · `backend` (Yadnesh) · `app` (Ojas, Android). Commit small and often to your own branch; merge to `main` at checkpoints (1:45, 2:45, 3:15).
