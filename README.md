# Veritas Lens — Explainable Deepfake & Identity Manipulation Forensics
**deepEntra Build Fest 2026 · CYB-03 · Team Masons**

A multi-signal forensic system that analyzes image/video samples for manipulation and reports **where** (face-region heatmaps, suspicious frames) and **why** (named forensic signals with measured reasons), with calibrated confidence, an honest evaluation (accuracy, false positives, failure cases) and a human review queue.

> Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer.

| Doc | For |
|---|---|
| [EXPLAINED.md](EXPLAINED.md) | Start here: the whole project explained from zero |
| [PLAN.md](PLAN.md) | Strategy, judging map, architecture, timeline, demo script |
| [CLAUDE.md](CLAUDE.md) | Full technical spec for coding agents (Claude Code / Antigravity via AGENTS.md) |
| [context/TRAINING_CONTEXT.md](context/TRAINING_CONTEXT.md) | Training / evaluation owner |
| [context/FRONTEND_CONTEXT.md](context/FRONTEND_CONTEXT.md) | Frontend / UI owner |
| [KICKOFF_PROMPTS.md](KICKOFF_PROMPTS.md) | Prompts to paste at 12:15 |
| [TEAM_SETUP.md](TEAM_SETUP.md) | Laptop setup + GitHub |

## Setup
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1      # add -Gpu for NVIDIA, -NoModels for frontend only
.venv\Scripts\python scripts\fetch_data.py                      # eval data (or copy data\ from the pen drive)
```
Models (~5 GB) and data are not committed; `scripts/download_models.py` and `scripts/fetch_data.py` recreate them.
