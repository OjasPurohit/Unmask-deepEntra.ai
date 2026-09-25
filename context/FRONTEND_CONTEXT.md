# Context: FRONTEND / UI owner — Veritas Lens (CYB-03)
> Paste into Antigravity as context (or @-mention this file). Also skim ../PLAN.md §0 and §6 (the demo script).

## Your mission in one line
Make the judges **see** the "where and why": heatmaps on the face, ranked suspicious regions, named signals with reasons, a frame timeline for video, an honest evaluation dashboard, and a human review queue. Demo & presentation is 20% of the score, and the UI carries most of it.

## Challenge requirements your screens must show
1. Image AND video analysis. 2. **Where** (region heatmap, suspicious frames) and **why** (signal + reason). 3. Confidence + failure cases + human review. 4. Accuracy / false positives / limits. 5. Guardrail wording (below), never "fake" or "proof".

## Stack
Vite + React + TypeScript + Tailwind + Recharts + react-router, in `frontend/`. Vite proxy `/api` → `http://localhost:8000`. Build against `src/mock.json` with `VITE_MOCK=1` from minute one, and don't wait for the backend.
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm i recharts react-router-dom && npm i -D tailwindcss @tailwindcss/vite
```

## Exact guardrail wording (copy verbatim)
| band | score | banner text | color |
|---|---|---|---|
| clean | < 0.35 | No strong manipulation indicators found | emerald |
| inconclusive | 0.35–0.70 | Inconclusive — human review required | amber |
| strong | > 0.70 | Strong manipulation indicators — human review required | rose |
Disclaimer on every result and on the printed report: **"Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer."**

## API (backend at :8000)
- `POST /api/analyze` (multipart `file`) → `AnalysisResult`
- `GET /api/samples` → `[{name, url, kind: "image"|"video", label_hint}]`
- `GET /api/cases` → `CaseSummary[]` · `GET /api/cases/{id}` → `AnalysisResult`
- `POST /api/cases/{id}/review` `{decision: "agree"|"disagree"|"needs_more", note}` → `Case`
- `GET /api/metrics` → metrics.json (shape in `context/TRAINING_CONTEXT.md` step 3)
- `GET /api/health` → `{models_loaded: bool, device: string}`

## `src/types.ts` (the contract; mirror of backend/schemas.py)
```ts
export type Band = "clean" | "inconclusive" | "strong";
export interface Signal { id: "classifier"|"ela"|"fft"|"noise"|"metadata"; name: string; score: number; weight: number;
  contribution: number; reason: string; heatmap?: string; panel?: string; details?: Record<string, unknown>; ok: boolean; error?: string }
export interface RegionScore { region: "left_eye"|"right_eye"|"mouth"|"nose"|"jaw_boundary"|"skin"|"background"; suspicion: number }
export interface FrameScore { t: number; score: number; thumb: string; heatmap?: string }
export interface Review { decision: "agree"|"disagree"|"needs_more"; note: string; at: string }
export interface AnalysisResult {
  case_id: string; sha256: string; filename: string; media_type: "image"|"video"; created_at: string;
  original: string;            // url of uploaded image (or a key frame for video)
  overlay: string;             // url of heatmap overlay, same size as original
  fused_score: number; band: Band; headline: string;   // e.g. "Suspicion concentrated at jaw boundary"
  signals: Signal[]; regions: RegionScore[];
  frames?: FrameScore[]; temporal?: { blink_rate_per_min: number; jitter: number; n_frames: number };
  robustness: { jpeg50: number; resize50: number };
  explanation: string; limitations: string[]; disclaimer: string;
  timings_ms: Record<string, number>; review?: Review;
}
export interface CaseSummary { case_id: string; filename: string; media_type: string; fused_score: number; band: Band; created_at: string; review?: Review }
```

## Screens
1. **Analyze** `/`: hero line ("Explainable manipulation forensics for identity verification"), drag-drop zone (image/video), a "Try a sample" gallery from `/api/samples`, and step progress while waiting: Detecting face → Running 5 forensic signals → Fusing evidence → Writing explanation. Then navigate to the report.
2. **Evidence report** `/case/:id`:
   - Top: BandBanner (band color + exact text) · ScoreGauge (fused score %) · headline · SHA-256 badge (truncated, copy button) · filename/time.
   - Left: **HeatmapViewer** showing the original with the overlay on top, an opacity slider (default 60%) and a side-by-side toggle.
   - Right: **RegionChips** ranked by suspicion (colored bars) · **SignalCards** (name, score bar, reason, click to expand the panel image + details; show "signal unavailable" if `ok=false`) · **ContributionBars** (how much each signal moved the score).
   - Video only: **FrameTimeline** (Recharts line of score vs t; clicking a point swaps the viewer to that frame's heatmap) + temporal stats.
   - Bottom: Explanation text · Robustness ("score after JPEG compression / downscale") · Limitations list · Disclaimer · **ReviewPanel** (3 buttons + note) · Print button.
   - A `@media print` stylesheet so browser Print → PDF gives a clean one-page evidence report.
3. **Evaluation** `/evaluation` (from `/api/metrics`): metric tiles (Accuracy, Precision, Recall, **False positive rate** highlighted, AUC) · ROC curve · confusion matrix (2×2 grid) · per-subset table · per-signal AUC bars (shows fused > single) · robustness table · **Failure gallery** (image + label + score + reason) · limitations · dataset source note.
4. **Review queue** `/review`: table of cases (thumb, file, band pill, score, review status), filter by band / unreviewed, click → report. Show the audit trail of review decisions.

## Design
Dark forensic-lab look: background `#0b1220`, cards `#111a2e` with 1px `#1f2a44` borders, teal accent `#14b8a6` (the CYB domain color), Inter font, generous spacing. Top nav: Analyze · Review queue · Evaluation · a small "Human-in-the-loop · Probabilistic" pill. Must look good at **1366×768** (projector). No lorem ipsum: the mock data should look real.

## `src/mock.json`
Build a realistic **strong-band face-swap** result: fused_score 0.82, headline "Suspicion concentrated at jaw boundary — consistent with face-swap blending", 5 signals (classifier 0.88, ela 0.64, fft 0.41, noise 0.71, metadata 0.2 with "No camera EXIF; re-encoded"), 7 regions (jaw_boundary highest), 8 frames with a spike at t=2.5, 3 limitations. Put placeholder images in `public/mock/`. Also add a mock metrics.json using the shape in TRAINING_CONTEXT.md.

## Checkpoints
1:45 all 4 screens on mock · 2:15 switched to the live API (`VITE_MOCK=0`) · 3:15 polish + print view. Never block on the backend: if a field is missing, render "—".
