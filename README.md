# Unmask — Explainable Deepfake & Identity Manipulation Forensics

> **⚠ SCOPE (26 Sep): Unmask is IMAGE-ONLY KYC identity-photo screening → face heatmap → KYC Verification Evidence Report. All video features below are REMOVED.**

**deepEntra Build Fest 2026 · CYB-03 · Team Masons**

A multi-signal forensic system that analyzes image/video samples for manipulation and reports **where** (face-region heatmaps, suspicious frames) and **why** (named forensic signals with measured reasons), with calibrated confidence, an honest evaluation (accuracy, false positives, failure cases) and a human review queue. Runs in the browser and as an **Android app** (Capacitor wrapping the same build; the models stay on the verification machine).

> Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer.

| Doc | For |
|---|---|
| [EXPLAINED.md](EXPLAINED.md) | Start here: the whole project explained from zero |
| [PLAN.md](PLAN.md) | Strategy, judging map, architecture, timeline, demo script |
| [CLAUDE.md](CLAUDE.md) | Full technical spec for coding agents (Claude Code / Antigravity via AGENTS.md) |
| [context/OMKAR_AI_MODELS.md](context/OMKAR_AI_MODELS.md) | **Omkar** — AI models: face detection, S1 (cf + probe), fusion, evaluation |
| [context/YADNESH_BACKEND.md](context/YADNESH_BACKEND.md) | **Yadnesh** — backend: ELA/FFT/noise/metadata, video, narrator, case store |
| [context/FRONTEND_OJAS_PALASH.md](context/FRONTEND_OJAS_PALASH.md) | **Ojas + Palash** — frontend, with the file-by-file ownership split |
| [context/ANDROID_APP.md](context/ANDROID_APP.md) | **Ojas + Palash** — the Capacitor Android app (same React build, phone as client) |
| [KICKOFF_PROMPTS.md](KICKOFF_PROMPTS.md) | One prompt per person to paste at 12:15 |
| [TEAM_SETUP.md](TEAM_SETUP.md) | Laptop setup, GitHub, Android toolchain |

## Setup
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1      # add -Gpu for NVIDIA, -NoModels for frontend only
.venv\Scripts\python scripts\fetch_data.py                      # eval data (or copy data\ from the pen drive)
```
Models (~5 GB) and data are not committed; `scripts/download_models.py` and `scripts/fetch_data.py` recreate them.

## Run
```powershell
# backend (http://localhost:8000, reachable over LAN for the phone)
.venv\Scripts\python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
# frontend (http://localhost:5173, proxies /api and /static to :8000)
cd frontend; npm i; npm run dev
# frontend on mock data, no backend needed
cd frontend; $env:VITE_MOCK="1"; npm run dev
```
Smoke test: `curl localhost:8000/api/health` · `curl -F "file=@selfie.jpg;type=image/jpeg" localhost:8000/api/analyze`.
The stubs in `backend/face.py`, `backend/signals/*.py`, `fusion.py`, `narrator.py` and `report.py` return plausible data; each owner replaces their own module while keeping the `run(img_rgb, face, case_dir) -> Signal` signature.
