# VERITAS LENS — Explainable Deepfake & Identity Manipulation Forensics
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
            ┌──────────── React (Vite+Tailwind) ────────────┐
            │ Analyze │ Evidence Report │ Eval Dashboard │ Review Queue │
            └───────────────────────┬───────────────────────┘
                                    │ REST (JSON below)
┌──────────────────────── FastAPI backend ──────────────────────────┐
│ ingest: sha256, type sniff, video→frames (OpenCV, 1–2 fps, ≤24)    │
│ face: MediaPipe FaceLandmarker → crop + region masks               │
│      (eyes, mouth, nose, jaw/face-boundary, skin, background)      │
│ SIGNALS (each returns score 0–1 + heatmap + 1-line reason):        │
│  S1 Deep classifier (HF ViT deepfake model) + OCCLUSION heatmap    │
│  S2 Error Level Analysis (JPEG re-save diff)                       │
│  S3 Frequency/FFT spectrum (GAN/diffusion upsampling peaks)        │
│  S4 Noise-residual inconsistency: face vs background               │
│  S5 Metadata/provenance: EXIF, editing software tags, C2PA         │
│  Video-only V1 per-frame score timeline, V2 blink rate (EAR),      │
│             V3 landmark jitter / temporal inconsistency            │
│ region attribution: heatmap ∩ region masks → "concentrated at jaw" │
│ fusion: logistic regression on [S1..S5] (fit on eval train split)  │
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
`GET /metrics` → metrics.json · `GET /cases` · `POST /cases/{id}/review` `{decision: agree|disagree|needs_more, note}` · `GET /cases/{id}/report` (printable HTML → browser Save-as-PDF).

## 3. Team split (4 people; 3 → merge B into A; 2 → drop S4, V3)
- **A — Detection core:** S1 classifier + occlusion heatmap (8×8 grid, gray patch, score drop), MediaPipe regions, region attribution.
- **B — Forensic signals + video:** S2 ELA, S3 FFT, S4 noise residual, S5 EXIF/C2PA, frame sampling, V1–V3.
- **C — Frontend:** 4 screens on mock JSON from minute 1. Heatmap overlay with opacity slider, signal contribution bars, region chips, frame timeline (Recharts), eval dashboard, review queue, printable report.
- **D — Data/eval/fusion/story (also demo lead):** eval.py, fusion LR, robustness run, narrator prompt + fallback, pitch, demo script, backup video recording.
Each person drives their own Antigravity/Claude Code agent with THIS FILE as context + their module's section.

## 4. Timeline (tomorrow)
| Time | Milestone |
|---|---|
| 10:00–11:00 | Check-in. Laptops up, envs verified, models load offline. |
| **11:00** | **Solution presentation (prepared today)** — problem, architecture, eval plan, VSS impact. |
| 12:00 | Mentor feedback → lock scope (keep P0, show P1 as plan). |
| 12:15–12:30 | Repo + folder skeleton + mock JSON + `/analyze` stub returning mock. |
| 12:30–1:45 | Parallel module build. Each signal = pure function `f(img, face) -> Signal`. |
| **1:45 CHECKPOINT** | Image end-to-end live (upload → real report). If not: cut S4/S5, keep going. |
| 1:45–2:45 | Video pipeline · eval.py runs over dataset (lunch) · fusion fit · narrator · review queue. |
| 2:45–3:15 | Polish UI, hero samples, record 90-s backup screen capture of the full demo. |
| **3:30 FREEZE** | No features. Rehearse demo twice with timer. |
| 4:00 | Demo. |

**P0 (must):** image upload, S1+occlusion heatmap, S2 ELA, S3 FFT, regions, fused band, report, eval dashboard with real numbers.
**P1:** video timeline + blink, S4, S5, narrator, review queue, robustness.
**P2 (only if ahead):** live webcam frame check for "interview mode", C2PA, PDF export.

## 5. Evaluation (this is the 25% "technical" proof — do it honestly)
- Set: ~150 real / ~150 manipulated images across subsets **[GAN faces, face-swap, diffusion-generated, edited/spliced]** + ~10/10 videos. Hold out 30% for test.
- Report: accuracy, precision, recall, **FPR** (the one VSS cares about — wrongly flagging a genuine applicant), ROC-AUC, confusion matrix, **per-subset breakdown**, threshold chosen for FPR ≤ 5%.
- Robustness: same metrics after JPEG q=50 and 50% resize → shows degradation curve.
- **Failure gallery:** 3–4 cases we get wrong + why (e.g., diffusion images the classifier never saw, heavy compression, side profile). Judges reward honesty; the problem statement literally asks for it.
- Fusion vs best single signal → shows the multi-signal design earns its keep.

## 6. Demo script (4 min, D presents, C drives)
1. (20s) Hook: "VSS admits students through applications and interviews. A face-swapped ID photo or a deepfaked video submission defeats that process in seconds."
2. (40s) Genuine photo → "No strong indicators", every signal green. Shows we don't cry wolf.
3. (60s) Face-swap → heatmap lights up jawline/face boundary, region chips, ELA + FFT panels, narrator explains in plain English, SHA-256 on report.
4. (40s) Video → frame timeline with spikes, click spike → heatmap of that frame, low blink rate noted.
5. (50s) Eval dashboard → real numbers, FPR, per-subset table, **the failure case** → "this is exactly why the system never decides; it routes to a human".
6. (30s) Review queue → reviewer disagrees, adds note, audit log. Close: guardrails + next step (pilot at VSS admissions desk; add more training data; C2PA provenance).

## 7. Risks → fallbacks
- Venue Wi-Fi dies → models + datasets cached locally; phone hotspot; narrator falls back to template.
- HF classifier generalizes badly → that's fine, fusion + other signals + honest per-subset table. Pick the best model TODAY.
- MediaPipe install issues → fall back to OpenCV Haar face detector (regions = fixed proportions of the box).
- Video too slow on CPU → cap at 16 frames, 224px, occlusion only on top-3 frames.
- Live demo breaks → play the backup recording, then continue with precomputed hero-sample reports.
