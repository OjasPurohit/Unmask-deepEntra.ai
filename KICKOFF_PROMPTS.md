# Kickoff prompts — paste at 12:15 PM
Each person opens the repo in Antigravity / Claude Code on their own branch and pastes THEIR prompt.
The agent automatically has CLAUDE.md + PLAN.md; the prompts only add the job.

---
## MASTER (Person A, first 15 min, on `main`) — scaffold so everyone can start in parallel
```
Read CLAUDE.md and PLAN.md fully. We have 3 hours. Scaffold the project exactly per the layout in CLAUDE.md:
1. backend/schemas.py with pydantic models Signal, RegionScore, FrameScore, AnalysisResult, ReviewIn, Case — matching PLAN.md §2 JSON exactly.
2. backend/app.py FastAPI with all routes from CLAUDE.md "API"; /api/analyze saves the upload to backend/static/cases/<case_id>/, computes sha256, and calls pipeline.analyze_image / analyze_video. Add CORS, static mount, /api/health.
3. backend/pipeline.py that runs every module in backend/signals/ inside try/except, times each, calls face.py, fusion.py, narrator.py, store.py. Each signal module starts as a stub returning a plausible Signal so the whole flow runs end-to-end now.
4. frontend/: Vite + React + TS + Tailwind + Recharts + react-router. src/types.ts mirroring schemas.py, src/mock.json with a realistic strong-band face-swap result (include 5 signals, 6 regions, 8 frames), src/api.ts that uses mock when VITE_MOCK=1. Vite proxy /api -> :8000. Empty pages: Analyze, Report, Evaluation, Review.
5. A root README.md run section: `.venv/Scripts/uvicorn backend.app:app --reload --port 8000` and `cd frontend && npm run dev`.
Run both servers, verify /api/health and one /api/analyze with a stub returns valid JSON, then commit "scaffold" and push.
```

---
## Person A — Detection core (branch `core`)
```
Read CLAUDE.md. Implement backend/face.py and backend/signals/classifier.py per the "Signal specs" (S1 + Regions) section.
- face.py: MediaPipe tasks FaceLandmarker (models/face_landmarker.task, IMAGE mode), return FaceInfo(box, crop_rgb, landmarks 478x2 px, masks dict name->bool array for left_eye, right_eye, mouth, nose, jaw_boundary, skin, background, yaw_estimate). Use FACEMESH index sets from the landmark topology (face oval, eyes, lips, nose). Fallback to OpenCV Haar + proportional regions if no landmarks.
- classifier.py: per CLAUDE.md "Benchmark finding": SigLIP backbone of models/prithivMLmods__deepfake-detector-model-v1 -> pooler_output embedding of the 224² face crop -> models/probe.joblib (StandardScaler+LogReg, trained by Person D's eval.py; until it exists train a quick one yourself from scripts/probe_experiment.py logic on all data). Secondary sub-score: haywoodsloan AI-generated model (p_fake normalization per CLAUDE.md). Load once, GPU if available. Occlusion heatmap 7x7 batched in a single forward pass. Save overlay png. Return sub-scores in details. Also expose predict_batch(list of images) for video + robustness.
- regions: function region_scores(heat, masks) -> sorted list[RegionScore] + headline sentence.
Test on 3 images from data/images/real and 3 from data/images/faceswap; print scores, timing and save overlays. Target < 2 s per image on GPU, < 8 s CPU. Commit.
```

## Person B — Forensic signals + video (branch `signals`)
```
Read CLAUDE.md. Implement backend/signals/ela.py, fft.py, noise.py, metadata.py, temporal.py exactly per "Signal specs", each following the Signal contract and never raising.
- Calibrate ELA/FFT/noise constants: write scripts/calibrate_signals.py that computes raw statistics over data/images/real and each fake subset and prints the separation; pick thresholds so real images mostly score < 0.35. Hard-code the chosen constants with a comment.
- Each signal saves a visual panel png (ELA map, log spectrum with azimuthal plot, noise residual heat) to case_dir.
- temporal.py: sample_frames(path, n=16) with timestamps; blink_rate(landmark sequence) via eye aspect ratio; jitter(landmark sequence). Use face.py and classifier.predict_batch from Person A (stub them if not merged yet).
Test on 2 real + 2 fake videos from data/videos. Commit.
```

## Person C — Frontend (branch `ui`)
```
Read CLAUDE.md "Frontend screens" and PLAN.md §6 demo script. Build all 4 screens in frontend/ against src/mock.json (VITE_MOCK=1), polished enough to demo to judges.
Dark forensic-lab look, teal accent #14b8a6, Inter font, cards with subtle borders. Components: BandBanner (color by band + exact wording + disclaimer), ScoreGauge, HeatmapViewer (original/overlay with opacity slider and side-by-side toggle), RegionChips, SignalCard (score bar, reason, panel image, expandable details), ContributionBars, FrameTimeline (Recharts line; click point -> show that frame's heatmap), LimitationsList, Sha256Badge, ReviewPanel (agree/disagree/needs_more + note), EvalDashboard (metric tiles, ROC curve, confusion matrix, per-subset table, robustness table, failure gallery), ReviewQueue table.
Analyze page: drag-drop + "Try a sample" gallery reading /api/samples (fallback to mock list) + step progress (Detecting face → Running 5 forensic signals → Fusing evidence → Writing explanation).
Report page must have a print stylesheet so browser Print -> PDF gives a clean evidence report.
Every screen must look good at 1366x768 (projector). Commit often.
```

## Person D — Eval, fusion, narrator, store (branch `eval`)
```
Read CLAUDE.md and PLAN.md §5. Implement:
1. scripts/eval.py: run the full pipeline (backend.pipeline) over data/images/* (label real=0, others=1) with a fixed 70/30 stratified split. On train split FIRST fit the S1 SigLIP probe (save models/probe.joblib; see CLAUDE.md benchmark finding + scripts/probe_experiment.py), then fit backend/fusion.py LogisticRegression on signal score vectors (save models/fusion.json with coefs + intercept). On test split compute: accuracy, precision, recall, FPR, FNR, ROC-AUC, ROC points, confusion matrix, per-subset metrics, each single signal's AUC vs fused AUC, robustness (JPEG q50 + 50% resize) metrics, threshold that gives FPR<=5%, and the 6 worst errors (store paths + scores + auto reason) as failure gallery. Also run over data/videos. Write backend/static/metrics.json. Cache per-image signal vectors to data/cache.json so re-runs are fast.
2. backend/fusion.py: load models/fusion.json; fused prob + per-signal contribution (coef*x); fallback fixed weights if file missing; band mapping per CLAUDE.md.
3. backend/narrator.py: build prompt from the AnalysisResult JSON only (no image), instruct: 4-6 sentences, cite measured signals and regions, state confidence band, mention limitations, never use words fake/proof/guilty/identity confirmed, end with human-review sentence. Gemini (google-genai) or Claude (anthropic) per .env, 8 s timeout, template fallback that produces a good paragraph deterministically.
4. backend/store.py: SQLite cases/reviews/audit_log; endpoints wiring with Person A's app.py.
5. /api/samples: list curated hero samples in backend/static/samples/ (copy 2 real, 2 faceswap, 1 inpainting, 1 text2img, 1 fake video, plus 1 known failure case chosen from eval).
Commit.
```

---
## Integration prompt (1:45 PM, on `main` after merging branches)
```
Merge state is on main. Run backend and frontend with VITE_MOCK=0. Upload each file in backend/static/samples through /api/analyze, fix every error until all return valid AnalysisResult and render on the Report page. Then run scripts/eval.py and make sure the Evaluation page renders real metrics. List anything still stubbed.
```

## Polish prompt (2:45 PM)
```
We freeze at 3:30. Walk the demo script in PLAN.md §6 end-to-end in the browser. Fix anything slow (>5 s image, >25 s video), ugly at 1366x768, or wording that violates the guardrail. Pre-analyze all hero samples at startup so the demo is instant. Do not add features.
```
