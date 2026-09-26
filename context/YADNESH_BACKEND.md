# Context: BACKEND + ML — Yadnesh · Unmask (CYB-03)
> Paste into Antigravity as context (or @-mention this file). Also read ../CLAUDE.md and ../PLAN.md.
> Branch: **`backend`**. Merge into `main` at 1:45 / 2:45 / 3:15.

## Your mission in one line
Own the **classic forensic signals, the KYC evidence report, the narrator and the case store**: everything that turns one classifier score into a multi-signal, explainable, reviewable case. S2–S5 are what make us "a forensic lab", not "a model with a percentage" — that is the 30% innovation score.

## What is already true (don't redo)
- Python 3.12 venv at `.venv`, all libraries installed (OpenCV, Pillow, piexif, scikit-learn, FastAPI). Models are in `models/`, data in `data/` (local only, pen drive).
- `Signal` is already defined in `backend/schemas.py` (Ojas's 12:15 scaffold) and mirrored in `frontend/src/types.ts`. **Do not change the contract** — ask Ojas.
- Every signal module is a stub returning a plausible `Signal` from minute one, so the pipeline runs end-to-end before you write anything. Replace stubs one at a time; the app never breaks.
- Data: `data/images/real` (350, varied sizes), `faceswap` / `inpainting` / `text2img` (100 each, all 512×512). (videos are out of scope)
- Guardrail wording is fixed (CLAUDE.md "Output bands & wording"). Reasons you write appear verbatim in the UI: never the words *fake*, *proof*, *guilty*, *identity confirmed*.

## The contract every signal obeys
```python
def run(img_rgb: np.ndarray, face: FaceInfo | None, case_dir: Path) -> Signal
# Signal(id, name, score 0..1 = suspicion, heatmap|panel url, reason (one measured sentence),
#        details: dict, ok: bool, error: str | None)
```
**Never raise.** Wrap the body in try/except and return `ok=False, error=str(e)`. A signal that fails must not take the pipeline down. `face` may be `None` (no face found) — degrade to whole-image statistics and say so in `reason`.

## Your build tasks, in order (P0 → P1)
### P0 — the three image signals that carry the demo
1. **`backend/signals/ela.py` (S2)** — re-save as JPEG q=90, `abs(orig - resaved) * 15`, score = mean ELA inside the face mask vs outside (ratio → sigmoid). Save the ELA image as the panel png. Reason like *"Error levels inside the face region are 2.4× the surrounding image — consistent with a re-encoded or pasted region."*
2. **`backend/signals/fft.py` (S3)** — grayscale face crop → 256², log-magnitude spectrum, azimuthal average; score from high-frequency energy ratio + count of periodic peaks against a real-image baseline. Save the spectrum png (with the azimuthal curve).
3. **`backend/signals/noise.py` (S4)** — residual = `img - cv2.medianBlur(img, 3)`; compare residual std inside the face mask vs a background ring; a large mismatch suggests splicing/swapping. Save a residual heat png.
4. **`scripts/calibrate_signals.py`** — compute the raw statistic of each of the three over `data/images/real` and each fake subset, print the separation and the suggested cut-offs, then **hard-code the chosen constants with a comment saying where they came from**. Target: most real images score < 0.35. Uncalibrated signals that flag every real photo are worse than no signal — the FPR is what VSS judges care about.

### P1
5. **`backend/signals/metadata.py` (S5)** — EXIF presence, `Software` tag (photoshop / gimp / stable diffusion / midjourney / dall·e), missing camera Make/Model, C2PA/JUMBF marker bytes in the file. **Low weight**; the value is the text (*"No camera EXIF; file re-encoded by an unknown tool"*), not the number. Never conclude from metadata alone.
6. **`backend/report.py` — KYC Verification Evidence Report** (replaces the old video task; video is out of scope). `render_report(result, review) -> str`, printable HTML served at `GET /api/cases/{id}/report`: header "KYC Verification Evidence Report" + case ID + timestamp + SHA-256; original image and heatmap overlay side by side; band banner with the exact wording; fused score; ranked face regions; one row per signal (score, reason, panel thumbnail); the narrator explanation; limitations; reviewer decision + note + time (or "Pending human review"); the disclaimer as the footer. Clean `@media print` CSS so browser Print → PDF gives a 1–2 page document. Images referenced by root-relative `/static/...` URLs.
7. **`backend/narrator.py`** — build the prompt from the `AnalysisResult` **JSON only** (never the image). Ask for 4–6 sentences that cite the measured signals and regions, state the confidence band, mention the limitations, and end with the human-review sentence. Banned words: fake, proof, guilty, identity confirmed. Gemini (`google-genai`) or Claude (`anthropic`) per `.env`, **8 s timeout**, and a deterministic template fallback that produces a genuinely good paragraph — assume the venue Wi-Fi dies, because it probably will.
8. **`backend/store.py` + routes** — SQLite with `cases`, `reviews`, `audit_log` (append-only: who/what/when for every analyze and every review). Wire `GET /api/cases`, `GET /api/cases/{id}`, `POST /api/cases/{id}/review` into Ojas's `app.py`, and `GET /api/cases/{id}/report` (printable HTML with the disclaimer). The audit trail is a direct answer to the security-governance judge.

## Interfaces you depend on / provide
- **You depend on:** `backend/schemas.py` (Ojas) · `backend/face.py` `FaceInfo(box, crop_rgb, landmarks, masks, yaw)` (Omkar). Stub both until they merge; do not edit their files.
- **You provide:** five working `run()` signals, `render_report()`, `narrate(result) -> str`, and a store Omkar's `scripts/eval.py` and Ojas's review queue both read.

## Files you own (nobody else edits them)
`backend/signals/ela.py`, `fft.py`, `noise.py`, `metadata.py` · `backend/report.py` · `backend/narrator.py` · `backend/store.py` · `scripts/calibrate_signals.py`.

## Checkpoints
**1:45** ELA + FFT + noise real (not stubs), calibrated, panels saving · **2:45** metadata + narrator + store/review routes + KYC report · **3:15** frozen; test 4 real and 4 manipulated images end-to-end and confirm no signal ever raises.
