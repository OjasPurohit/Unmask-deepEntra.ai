# UNMASK — Explainable Deepfake & Identity Manipulation Forensics
deepEntra Build Fest 2026 · CYB-03 · Build window 12:15 → 3:30 PM (3h15m real)

## 0. How we win (read the scorecard, not the problem statement)
| Criterion | Weight | What judges must SEE |
|---|---|---|
| Innovation | 30% | Not "a classifier with a %". A **multi-signal forensic lab**: 5 independent detectors → region-level "where & why" → evidence report. LLM is only the *narrator* of measured evidence, never the detector. |
| Technical execution | 25% | It actually works live on image **and** video. A real eval set with accuracy / FPR / ROC / confusion matrix. A robustness test (JPEG/resize) that honestly shows where it breaks. |
| Real-world impact (VSS!) | 25% | Framed for **VSS admissions**: verifying applicant ID photos and online interview/video submissions. Human review queue, audit trail, SHA-256 chain-of-custody. |
| Demo | 20% | 4-minute story: real → clean, face-swap → heatmap on jawline, video → spike timeline, eval dashboard → honest failure → "that's why a human decides". |

Judges: 2 VSS trustees (Gogte, Ranjankar) → impact for VSS. IBM security-governance architect (Mandar Modak) → guardrails, audit, calibrated confidence. Lots of product people (Bapat x2, Baxi, Sumant, Kulkarni) → clean UX + clear story. deepEntra founder → "Ship working AI".

**Guardrail language (use everywhere, never say "fake"/"proof"):**
- `< 0.35` → "No strong manipulation indicators found"
- `0.35–0.70` → "Inconclusive — human review required"
- `> 0.70` → "Strong manipulation indicators — human review required"
- Footer on every report: *"Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer."*

## 1. Architecture
```
   ┌─── React (Vite+Tailwind) — web AND Android (Capacitor APK) ───┐
   │ Analyze │ Evidence Report │ Eval Dashboard │ Review │ Settings │
   └───────────────────────────────┬───────────────────────────────┘
                                   │ REST — localhost (web) / LAN (phone)
┌──────────────────────── FastAPI backend ──────────────────────────┐
│ ingest: sha256, type sniff, video→frames (OpenCV, 1–2 fps, ≤24)    │
│ face: MediaPipe FaceLandmarker → crop + region masks               │
│      (eyes, mouth, nose, jaw/face-boundary, skin, background)      │
│ SIGNALS (each returns score 0–1 + heatmap + 1-line reason):        │
│  S1 cf (CommunityForensics ViT, full image) + probe (face-crop     │
│     embedding) + OCCLUSION heatmap; UI score = max(cf, probe)      │
│  S2 Error Level Analysis (JPEG re-save diff)                       │
│  S3 Frequency/FFT spectrum (GAN/diffusion upsampling peaks)        │
│  S4 Noise-residual inconsistency: face vs background               │
│  S5 Metadata/provenance: EXIF, editing software tags, C2PA         │
│  Video-only V1 per-frame score timeline, V2 blink rate (EAR),      │
│             V3 landmark jitter / temporal inconsistency            │
│ region attribution: heatmap ∩ region masks → "concentrated at jaw" │
│ fusion: logistic regression on cf, probe, ela, fft, noise,         │
│         metadata (fit on the eval train split)                     │
│         → calibrated prob + per-signal contribution bars           │
│ narrator: Gemini/Claude gets ONLY the JSON → plain-language report │
│           (template fallback if API is down)                       │
│ store: SQLite/JSON — cases, reviewer decisions, audit log          │
│ eval: scripts/eval.py → metrics.json (precomputed, shown in UI)    │
└────────────────────────────────────────────────────────────────────┘
```

## 2. API contract (freeze at 12:20 — frontend builds on a mock of this)
`POST /analyze` (multipart `file`) → 
```json
{
  "case_id": "C-0007", "sha256": "…", "media_type": "image|video",
  "fused_score": 0.82, "band": "strong|inconclusive|clean",
  "signals": [
    {"id":"classifier","name":"Deep classifier","score":0.91,"weight":0.4,
     "details":{"cf":0.44,"probe":0.91},
     "reason":"Model activation concentrated on face boundary","heatmap":"/static/C-0007/cls.png"},
    {"id":"ela","score":0.6, "...":"..."}, {"id":"fft"}, {"id":"noise"}, {"id":"metadata"}
  ],
  "regions": [{"region":"jaw_boundary","suspicion":0.78},{"region":"eyes","suspicion":0.31}],
  "frames": [{"t":1.5,"score":0.88,"thumb":"/static/…"}],          // video only
  "temporal": {"blink_rate_per_min":3.1,"jitter":0.42},            // video only
  "robustness": {"jpeg50":0.74,"resize50":0.69},
  "explanation": "…", "limitations": ["Low-res input (<256px face)", "…"],
  "disclaimer": "Probabilistic forensic indicators only…"
}
```
`GET /metrics` → metrics.json · `GET /samples` · `GET /cases` · `POST /cases/{id}/review` `{decision: agree|disagree|needs_more, note}` · `GET /cases/{id}/report` (printable HTML → browser Save-as-PDF) · `GET /health`.
All routes are served under `/api`. CORS is open and uvicorn binds `0.0.0.0` so the Android client can reach them over LAN; all image URLs are root-relative (`/static/...`) and the client prefixes its own base.

## 3. Team (4 people) — who builds what
| Person | Role | Owns | Branch | Context file |
|---|---|---|---|---|
| **Ojas** | Team lead / architect · frontend · Android | 12:15 MASTER scaffold (repo skeleton, `backend/schemas.py` mirroring `types.ts`, `app.py` routes, `pipeline.py` orchestration with stubs, frontend Vite skeleton). Then frontend **with** Palash: Evaluation page, Review queue page, Settings, app shell, **the Android app**. Merges at 1:45 / 2:45 / 3:15, integration testing, hero samples, the 11:00 pitch and the 4:00 demo. | `main` (scaffold/merges) + `app` (Android) | `context/FRONTEND_OJAS_PALASH.md` + `context/ANDROID_APP.md` |
| **Palash** | Frontend · Android UI | Design system / theme, shared components, **Analyze page**, **Evidence Report page** (the demo centrepiece), mobile-responsive layout and the mobile camera/upload flow the Android app uses. | `ui` | `context/FRONTEND_OJAS_PALASH.md` + `context/ANDROID_APP.md` |
| **Omkar** | AI models | `backend/face.py` (MediaPipe landmarks, crop, region masks), `backend/signals/classifier.py` (S1 = `cf` + `probe`, occlusion heatmap, region attribution), probe training, `scripts/eval.py`, `backend/fusion.py`, `metrics.json`, failure gallery, robustness. | `models` | `context/OMKAR_AI_MODELS.md` |
| **Yadnesh** | Backend · ML | `backend/signals/ela.py`, `fft.py`, `noise.py`, `metadata.py` (+ `scripts/calibrate_signals.py`), `temporal.py` (video frames, blink rate, jitter), `narrator.py` (LLM + template fallback), `store.py` (SQLite cases/reviews/audit) and those routes. | `backend` | `context/YADNESH_BACKEND.md` |

Everyone drives their own Antigravity / Claude Code agent with `CLAUDE.md` + this file + their own context file. Prompts to paste: `KICKOFF_PROMPTS.md`.
Down a person: Omkar absorbs Yadnesh's S4/S5, Ojas absorbs the video pipeline. Down two: drop S4, V3 and the Android app.

### 3.1 File → owner (nobody edits someone else's file; ask instead)
| File | Owner |
|---|---|
| `backend/schemas.py` | **Ojas** (THE contract) |
| `frontend/src/types.ts` | **Ojas** (mirror of schemas.py) |
| `backend/app.py` | Ojas |
| `backend/pipeline.py` | Ojas |
| `backend/face.py` | Omkar |
| `backend/signals/classifier.py` | Omkar |
| `backend/fusion.py` | Omkar |
| `backend/signals/ela.py` · `fft.py` · `noise.py` · `metadata.py` · `temporal.py` | Yadnesh |
| `backend/narrator.py` | Yadnesh |
| `backend/store.py` | Yadnesh |
| `backend/static/metrics.json` | Omkar |
| `backend/static/samples/` | Ojas (files) — chosen with Omkar |
| `scripts/embed.py` · `train_probe.py` · `eval.py` · `probe_experiment.py` · `benchmark_models.py` | Omkar |
| `scripts/calibrate_signals.py` | Yadnesh |
| `scripts/setup.ps1` · `download_models.py` · `fetch_data.py` | Ojas |
| `frontend/src/api.ts` | Ojas |
| `frontend/src/App.tsx` · `main.tsx` · `vite.config.ts` | Ojas |
| `frontend/src/pages/Evaluation.tsx` · `Review.tsx` · `Settings.tsx` | Ojas |
| `frontend/src/pages/Analyze.tsx` · `Report.tsx` | Palash |
| `frontend/src/components/*` | Palash |
| `frontend/src/theme.ts` · `index.css` · Tailwind config | Palash (builds first; Ojas imports) |
| `frontend/src/mock.json` | Palash |
| `frontend/capacitor.config.ts` · `frontend/android/` | Ojas |


## 4. Timeline (tomorrow)
| Time | Milestone |
|---|---|
| 10:00–11:00 | Check-in. Laptops up, envs verified, models load offline. |
| **11:00** | **Solution presentation (prepared today)** — problem, architecture, eval plan, VSS impact. |
| 12:00 | Mentor feedback → lock scope (keep P0, show P1 as plan). |
| 12:15–12:30 | **Ojas** pastes the MASTER prompt: repo + folder skeleton + mock JSON + `/analyze` stub returning mock. Everyone pulls. |
| 12:30–1:45 | Parallel module build. Each signal = pure function `f(img, face) -> Signal`. |
| **1:45 CHECKPOINT** | Image end-to-end live (upload → real report). If not: cut S4/S5, keep going. |
| 1:45–2:45 | Video pipeline · eval.py runs over dataset (lunch) · fusion fit · narrator · review queue. **Android build starts (P1.5): Ojas `npx cap add android`, first APK on the phone.** |
| 2:45–3:00 | APK rebuilt from merged `main`, installed on the demo phone, one real analysis end-to-end. **APK frozen at 3:00.** |
| 2:45–3:15 | Polish UI, hero samples, record 90-s backup screen capture of the full demo (including the phone beat). |
| **3:30 FREEZE** | No features. Rehearse demo twice with timer. |
| 4:00 | Demo. |

**P0 (must):** image upload, S1+occlusion heatmap, S2 ELA, S3 FFT, regions, fused band, report, eval dashboard with real numbers.
**P1:** video timeline + blink, S4, S5, narrator, review queue, robustness.
**P1.5 (Android APK):** start only after the 1:45 checkpoint passes on web; target a working APK by 3:00. It is a 30-s demo beat, not a dependency — if it slips, the fallback in §7 costs us nothing. Spec: `context/ANDROID_APP.md`.
**P2 (only if ahead):** live webcam frame check for "interview mode", C2PA, PDF export.

## 5. Evaluation (this is the 25% "technical" proof — do it honestly)
- Set: ~150 real / ~150 manipulated images across subsets **[GAN faces, face-swap, diffusion-generated, edited/spliced]** + ~10/10 videos. Hold out 30% for test.
- Report: accuracy, precision, recall, **FPR** (the one VSS cares about — wrongly flagging a genuine applicant), ROC-AUC, confusion matrix, **per-subset breakdown**, threshold chosen on the train split for FPR ≤ 10% (see CLAUDE.md).
- Robustness: same metrics after JPEG q=50 and 50% resize → shows degradation curve.
- **Failure gallery:** 3–4 cases we get wrong + why (e.g., diffusion images the classifier never saw, heavy compression, side profile). Judges reward honesty; the problem statement literally asks for it.
- Fusion vs best single signal → shows the multi-signal design earns its keep.

## 6. Demo script (4 min = 240 s · Ojas presents, Palash drives the laptop, Yadnesh holds the phone)
1. (20s) Hook: "VSS admits students through applications and interviews. A face-swapped ID photo or a deepfaked video submission defeats that process in seconds."
2. (35s) Genuine photo → "No strong indicators", every signal green. Shows we don't cry wolf.
3. (55s) Face-swap → heatmap lights up jawline/face boundary, region chips, ELA + FFT panels, narrator explains in plain English, SHA-256 on report.
4. (35s) Video → frame timeline with spikes, click spike → heatmap of that frame, low blink rate noted.
5. (30s) **Phone app** → "a VSS admissions officer verifies an applicant photo from a phone": open the Unmask APK, tap upload / camera, the band banner and heatmap appear on the phone, and the case lands in the review queue on the projector. Say the line: *"the models never leave the verification machine — the phone is just a secure client."*
6. (45s) Eval dashboard → real numbers, FPR, per-subset table, the "combining helps" table (`cf` vs `probe` vs fused), **the failure case** → "this is exactly why the system never decides; it routes to a human".
7. (20s) Review queue → reviewer disagrees, adds note, audit log. Close: guardrails + next step (pilot at VSS admissions desk; more training data; C2PA provenance).


## 7. Risks → fallbacks
- Venue Wi-Fi dies → models + datasets cached locally; phone hotspot; narrator falls back to template.
- HF classifier generalizes badly → that's fine, fusion + other signals + honest per-subset table. Pick the best model TODAY.
- MediaPipe install issues → fall back to OpenCV Haar face detector (regions = fixed proportions of the box).
- Video too slow on CPU → cap at 16 frames, 224px, occlusion only on top-3 frames.
- Live demo breaks → play the backup recording, then continue with precomputed hero-sample reports.
- **APK does not build or install in time** → drop the 30-s phone beat to the web app open in the phone browser at `http://<laptop-LAN-IP>:5173`. Same UI, same story, say it as "the same client, unpackaged". Keep a second phone with the APK preinstalled as backup.
- **Venue Wi-Fi blocks device-to-device traffic** (common on guest networks) → put the laptop on the demo phone's hotspot instead; get the LAN IP again with `ipconfig` and change it in the app's Settings field.
