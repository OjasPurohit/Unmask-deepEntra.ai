# Kickoff prompts — paste at 12:15 PM
One prompt per person. Each opens the repo in Antigravity / Claude Code **on their own branch** and pastes THEIR prompt.
`AGENTS.md` already points every agent at `CLAUDE.md` + `PLAN.md`; each prompt names the extra context file to read.

| Person | Branch | Context file(s) | Prompts below |
|---|---|---|---|
| Ojas | `main`, then `app` | `context/FRONTEND_OJAS_PALASH.md`, `context/ANDROID_APP.md` | 1 (MASTER), 2, 6, 7 |
| Palash | `ui` | `context/FRONTEND_OJAS_PALASH.md`, `context/ANDROID_APP.md` | 3 |
| Omkar | `models` | `context/OMKAR_AI_MODELS.md` | 4 |
| Yadnesh | `backend` | `context/YADNESH_BACKEND.md` | 5 |

---
## 1. OJAS — MASTER scaffold (12:15, first 15 min, on `main`)
```
Read CLAUDE.md and PLAN.md fully, plus context/FRONTEND_OJAS_PALASH.md and context/ANDROID_APP.md. We have 3 hours and three people waiting on this scaffold, so build it fast and push.
1. backend/schemas.py with pydantic models Signal, RegionScore, FrameScore, Review, AnalysisResult, CaseSummary — matching the types.ts block in context/FRONTEND_OJAS_PALASH.md EXACTLY (it is the contract; I own both sides of it).
2. backend/app.py FastAPI with every route from CLAUDE.md "API": /api/analyze saves the upload to backend/static/cases/<case_id>/, computes sha256, calls pipeline.analyze_image / analyze_video. Plus /api/cases, /api/cases/{id}, /api/cases/{id}/review, /api/cases/{id}/report, /api/metrics, /api/samples, /api/health. CORSMiddleware with allow_origins=["*"], all methods and headers (the Android webview needs it). Mount /static. Every image path in a response must be root-relative "/static/...".
3. backend/pipeline.py: run face.py then every module in backend/signals/ inside try/except, time each one, then fusion.py, narrator.py, store.py. Each signal module starts as a STUB returning a plausible Signal so the whole flow runs end-to-end right now — Omkar and Yadnesh replace the stubs one file at a time without ever breaking the app. The classifier stub must return details {"cf": ..., "probe": ...} with score = max of the two.
4. frontend/: Vite + React + TS + Tailwind + Recharts + react-router. src/types.ts mirroring schemas.py; src/api.ts with a single BASE = localStorage unmask_api, else import.meta.env.VITE_API_BASE, else "" — plus an apiUrl(path) helper that EVERY image/static URL goes through; src/mock.json with a realistic strong-band face-swap result (5 signals including classifier details cf/probe, 7 regions, 8 frames); mock used when VITE_MOCK=1. Vite proxy /api -> :8000. Empty routed pages: Analyze, Report, Evaluation, Review, Settings.
5. README run section: uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000, and cd frontend && npm run dev.
Run both servers, verify /api/health and one /api/analyze returns valid JSON, then commit "scaffold" and push to main. Tell the team to pull.
```

## 2. OJAS — frontend (after the scaffold, on `main`)
```
Read context/FRONTEND_OJAS_PALASH.md. I own the Evaluation page, Review queue, Settings, the app shell, src/types.ts and src/api.ts. Palash owns the theme, the shared components, Analyze and Report — never edit his files; ask him instead.
Against src/mock.json and a mock metrics.json:
1. src/pages/Evaluation.tsx from /api/metrics: metric tiles (Accuracy, Precision, Recall, False positive rate HIGHLIGHTED, AUC), ROC curve, 2x2 confusion matrix, per-subset table, per-signal AUC bars showing cf vs probe vs each forensic signal vs fused, robustness table, failure gallery (image + true label + score + reason), limitations, dataset source note.
2. src/pages/Review.tsx: cases table (thumb, file, band pill, score, review status), filter by band / unreviewed, click -> report, and the audit trail of decisions.
3. src/pages/Settings.tsx: backend URL field saved to localStorage under unmask_api, Save / Reset, and a "Test connection" button hitting /api/health that shows models_loaded and device. This is what makes the phone demo survive an unknown venue IP.
4. App shell + routing + nav (Analyze · Review · Evaluation · Settings, plus the "Human-in-the-loop · Probabilistic" pill), importing Palash's theme and components — do not restyle them.
Every page must work at 1366x768 AND at 390px. Use Palash's components wherever one exists; if you need a new shared component, ask him rather than adding it to src/components.
The Android app is P1.5 and comes after the 1:45 checkpoint — do not start it now.
```

## 3. PALASH — design system, Analyze, Report, mobile (branch `ui`)
```
Read CLAUDE.md "Frontend screens", context/FRONTEND_OJAS_PALASH.md and PLAN.md §6 (the demo script). I own the theme, all shared components, the Analyze page and the Evidence Report page. Ojas owns Evaluation, Review, Settings, the app shell, types.ts and api.ts — never edit his files. Build against src/mock.json with VITE_MOCK=1; never wait on the backend.
FIRST, within 20 minutes, because Ojas imports them: src/theme.ts + src/index.css + Tailwind config. Dark forensic-lab look, background #0b1220, cards #111a2e with 1px #1f2a44 borders, teal accent #14b8a6, Inter, generous spacing.
THEN the shared components in src/components/: BandBanner (band color + the EXACT wording from CLAUDE.md + disclaimer), ScoreGauge, HeatmapViewer (original + overlay, opacity slider default 60%, side-by-side toggle), RegionChips, SignalCard (score bar, reason, expandable panel image + details, "signal unavailable" when ok=false; on the classifier card also show the cf and probe sub-scores from details), ContributionBars, FrameTimeline (Recharts line; click a point -> that frame's heatmap), LimitationsList, Sha256Badge, ReviewPanel, and Card/Pill/Table primitives.
THEN src/pages/Analyze.tsx: hero line "Explainable manipulation forensics for identity verification", drag-drop zone, a "Try a sample" gallery from /api/samples (fallback to a mock list), and step progress while waiting: Detecting face -> Running 5 forensic signals -> Fusing evidence -> Writing explanation.
THEN src/pages/Report.tsx — the demo centrepiece: band banner, gauge, headline, SHA-256 badge with copy, HeatmapViewer, ranked region chips, signal cards, contribution bars, video frame timeline + temporal stats, explanation, robustness, limitations, disclaimer, ReviewPanel, and a Print button with a @media print stylesheet that yields a clean one-page evidence report.
MOBILE IS A REQUIREMENT, not a nice-to-have: the Android APK wraps this exact build. Every page must be usable at 390px (nav collapses, viewer and slider stack vertically, tables scroll inside their own overflow-x-auto container), and the upload input must be an input type=file with accept="image/*,video/*" and capture so the phone camera opens directly. Build every image src through the apiUrl() helper in api.ts — never a bare "/static/..." path, it breaks inside the Android webview.
Must also look good at 1366x768 (projector). Commit often.
```

## 4. OMKAR — detection core + evaluation (branch `models`)
```
Read CLAUDE.md (especially "Models", the Benchmark finding, and "Signal specs" S1 + Regions) and context/OMKAR_AI_MODELS.md. You own backend/face.py, backend/signals/classifier.py, backend/fusion.py and the scripts; do not edit other people's files.
1. backend/face.py: MediaPipe tasks FaceLandmarker (models/face_landmarker.task, IMAGE mode — the legacy mp.solutions API does NOT exist in mediapipe 1.x). Return FaceInfo(box, crop_rgb = 1.3x landmark box resized to 224, landmarks 478x2 px, masks dict for left_eye, right_eye, mouth, nose, jaw_boundary (band along the face oval, +-6% face width), skin (oval minus features) and background, plus a yaw estimate). Fall back to OpenCV Haar + proportional regions if no landmarks, and flag that as a limitation.
2. backend/signals/classifier.py — S1 has TWO sub-scores:
   - cf = models/buildborderless__CommunityForensics-DeepfakeDet-ViT on the FULL image (no crop), loaded with function_to_apply="sigmoid"; its single sigmoid output already IS P(manipulated). Measured AUC 0.66 faceswap / 0.99 inpainting / 1.00 text2img at 0.3% FPR.
   - probe = a linear probe (StandardScaler + LogisticRegression C=0.1, models/probe.joblib) on the frozen haywoodsloan SwinV2 backbone embedding of the 224 face crop. Measured 0.87 / 0.88 / 0.95. Switch the backbone to SigLIP or to both concatenated only if that wins on the train split.
   - Put both in Signal.details as {"cf": ..., "probe": ...}; they enter fusion as TWO SEPARATE FEATURES. The score shown in the UI is max(cf, probe).
   - Occlusion heatmap computed on WHICHEVER SUB-SCORE IS HIGHER: 7x7 grid, patch filled with the image-mean color, heat = max(0, p_base - p_occluded), all 49 crops batched in ONE forward pass. Upsample, blur, JET colormap, alpha-blend 45%, save the overlay png. (cf occludes the full image; probe occludes the face crop.)
   - Also expose predict_batch(list of images) -> list of floats, for Yadnesh's video timeline and for robustness.
   - Load every model once at startup, local_files_only=True, GPU if available. Target under 2 s/image on GPU, under 8 s on CPU.
3. region_scores(heat, masks) -> sorted list[RegionScore] plus a headline sentence such as "Suspicion concentrated at jaw boundary — consistent with face-swap blending". That sentence is the centrepiece of the demo, so make it read well.
4. Then the numbers, per context/OMKAR_AI_MODELS.md: scripts/embed.py, scripts/train_probe.py (fixed stratified 70/30 split, seed 7; threshold chosen on the TRAIN split for FPR <= 10%), scripts/eval.py -> backend/static/metrics.json with exactly the documented keys, backend/fusion.py (LogisticRegression over [cf, probe, ela, fft, noise, metadata] + fixed-weight fallback + band mapping), robustness (JPEG q50 and 50% resize), the 6-case failure gallery, and the team-selfie out-of-distribution check.
LEAKAGE GUARD: all fakes are 512x512 while reals vary, so ALWAYS face-crop and resize to 224 before any model, and never feed image size or format as a feature.
Test on 3 images from data/images/real and 3 from data/images/faceswap; print scores, both sub-scores and timings, and save the overlays. Commit.
```

## 5. YADNESH — forensic signals, video, narrator, store (branch `backend`)
```
Read CLAUDE.md "Signal specs" and context/YADNESH_BACKEND.md. You own backend/signals/ela.py, fft.py, noise.py, metadata.py, temporal.py, plus backend/narrator.py, backend/store.py and scripts/calibrate_signals.py; do not edit other people's files. Every module follows the Signal contract in CLAUDE.md and NEVER raises — wrap the body in try/except and return ok=False with the error. `face` may be None; degrade to whole-image statistics and say so in the reason.
1. ela.py (S2): re-save JPEG q=90, abs diff x15, score = mean ELA inside the face vs outside (ratio -> sigmoid), save the ELA panel png.
2. fft.py (S3): grayscale face crop at 256x256, log-magnitude spectrum, azimuthal average, score from the high-frequency energy ratio + periodic peak count against a real-image baseline, save the spectrum png.
3. noise.py (S4): residual = img - medianBlur(img, 3); compare residual std inside the face mask against a background ring; save a residual heat png.
4. scripts/calibrate_signals.py: compute each raw statistic over data/images/real and each fake subset, print the separation, pick cut-offs so most REAL images score below 0.35, then hard-code the constants with a comment saying where they came from. False positives are the metric the VSS judges care about.
5. metadata.py (S5): EXIF presence, Software tag (photoshop / gimp / stable diffusion / midjourney / dall-e), missing camera Make/Model, C2PA/JUMBF marker bytes. Low weight; the value is the sentence, not the number. Never conclude from metadata alone.
6. temporal.py (V1-V3): sample_frames(path, n=16) with timestamps (cv2); per-frame S1 score via classifier.predict_batch -> timeline; blink rate via eye aspect ratio over the landmark sequence (human is roughly 15-20/min; under 5 is a WEAK indicator only, and the reason must say so); landmark jitter = mean frame-to-frame displacement normalized by face width. Video fused score = 0.6*mean(top-25% frames) + 0.4*temporal. Stub Omkar's face.detect and classifier.predict_batch behind a small adapter until the models branch merges.
7. narrator.py: prompt built from the AnalysisResult JSON ONLY (never the image). 4-6 sentences citing the measured signals and regions, stating the confidence band, mentioning the limitations, ending with the human-review sentence. Banned words: fake, proof, guilty, identity confirmed. Gemini (google-genai) or Claude (anthropic) per .env, 8 s timeout, and a deterministic template fallback that reads well — assume the venue Wi-Fi dies.
8. store.py: SQLite cases / reviews / audit_log (append-only, timestamped), wired into Ojas's app.py routes, plus the printable HTML report.
Test on 2 real and 2 fake videos from data/videos and confirm no signal ever raises. Commit.
```

---
## 6. Integration (1:45 PM · Ojas, on `main` after merging `ui`, `models`, `backend`)
```
Integration checkpoint. Read CLAUDE.md and PLAN.md (§3.1 file ownership).
1. MERGE: git fetch origin, make sure main is clean, then merge origin/models, origin/backend and origin/ui into main one at a time. On conflict: the file owner in PLAN.md §3.1 wins; for schemas.py / types.ts (the contract, owned by Ojas) keep main's version and adapt the other code to it. Never delete someone's work to make a merge pass. Report every conflict you resolved.
2. RUN: start the backend (.venv/Scripts/uvicorn backend.app:app --host 0.0.0.0 --port 8000) and the frontend with VITE_MOCK=0. Fix startup errors first.
3. END-TO-END: upload every file in backend/static/samples (or 2 images from data/images/real and 2 from data/images/faceswap if samples don't exist yet) through /api/analyze. Fix errors until each returns a valid AnalysisResult that renders fully on the Report page: band banner, heatmap overlay, region chips, all signal cards (classifier card shows cf and probe), explanation, limitations, SHA-256, disclaimer. A failing signal must show as "unavailable", never crash the page.
4. EVALUATION: if scripts/eval.py exists, check backend/static/metrics.json is present and the Evaluation page renders real numbers. Don't re-run a long eval unless metrics.json is missing.
5. VIDEO: upload one video from data/videos and check the frame timeline renders.
6. CHECK: every page at 1366x768; timings (image < 5 s, video < 25 s); grep user-facing text in frontend and backend for guardrail violations (fake / proof / guilty / identity confirmed).
7. REPORT: a short list of what works, what's still a stub, and who owns each remaining problem (per PLAN.md §3.1). Then commit "integration checkpoint <time>" and push main.
Only fix what's needed to make the merged app run. Don't add features.
```

## 7. Android APK (2:45 PM · Ojas, branch `app` — only if the 1:45 checkpoint passed)
```
Read context/ANDROID_APP.md. Wrap the existing frontend build into an Android APK with Capacitor — no separate native codebase, and no model on the phone.
1. cd frontend && npm i @capacitor/core @capacitor/cli @capacitor/android && npx cap init "Unmask" ai.unmask.app --web-dir dist
2. capacitor.config.ts: appId ai.unmask.app, appName "Unmask", webDir 'dist', server: { cleartext: true }. Also set android:usesCleartextTraffic="true" on the <application> element in android/app/src/main/AndroidManifest.xml — the backend is plain http on the LAN and Android blocks it otherwise.
3. Confirm the backend has CORS allow_origins=["*"] and runs with --host 0.0.0.0, and that the Windows firewall allows inbound TCP 8000: New-NetFirewallRule -DisplayName "Unmask 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow. Get the laptop LAN IP with ipconfig.
4. frontend/.env.production: VITE_API_BASE=http://<laptop-LAN-IP>:8000
5. npm run build, then npx cap add android, npx cap sync android, then cd android and .\gradlew assembleDebug
6. APK lands at android/app/build/outputs/apk/debug/app-debug.apk — install with adb install -r, or copy the file to the phone and tap it.
Verify on the phone: the Settings page can change the backend URL at runtime, the camera opens from the upload button, one real image goes end-to-end, and the case appears in the review queue on the laptop. If the build fails, stop at 3:00 and use the fallback (the web app in the phone browser at the laptop IP) — do not let this eat demo-rehearsal time.
```

## 8. Polish (3:00 PM · everyone, on `main`)
```
We freeze at 3:30. Walk the demo script in PLAN.md §6 end-to-end in the browser AND once on the phone. Fix anything slow (over 5 s for an image, over 25 s for a video), anything ugly at 1366x768 or 390px, and any wording that violates the guardrail. Pre-analyze all hero samples at startup so the demo is instant. Record the 90-second backup screen capture. Do not add features.
```
