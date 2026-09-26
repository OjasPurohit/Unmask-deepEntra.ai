"""Unmask API. Run: .venv/Scripts/python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload"""
import hashlib
import json
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend import pipeline, report, store
from backend.schemas import AnalysisResult, CaseSummary, ReviewIn

logging.basicConfig(level=logging.INFO)
STATIC = pipeline.STATIC
CASES = STATIC / "cases"
CASES.mkdir(parents=True, exist_ok=True)
EXTS = {".jpg", ".jpeg", ".png", ".webp"}

app = FastAPI(title="Unmask")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _get(case_id: str) -> AnalysisResult:
    r = store.get(case_id)
    if not r:
        raise HTTPException(404, "Case not found")
    return r


@app.get("/api/health")
def health():
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001
        device = "cpu"
    return {"models_loaded": False, "device": device}


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if not (file.content_type or "").startswith("image/") or ext not in EXTS:
        raise HTTPException(415, "Images only (jpg, png, webp)")
    data = await file.read()
    case_id = uuid.uuid4().hex[:12]
    case_dir = CASES / case_id
    case_dir.mkdir(parents=True)
    path = case_dir / f"original{ext}"
    path.write_bytes(data)
    try:
        result = pipeline.analyze_image(path, case_id, hashlib.sha256(data).hexdigest(), file.filename or path.name)
    except ValueError as e:
        raise HTTPException(422, str(e))
    store.save(result)
    return result


@app.get("/api/samples")
def samples():
    return [{"name": p.stem, "url": f"/static/samples/{p.name}", "kind": "image", "label_hint": p.stem.split("_")[0]}
            for p in sorted((STATIC / "samples").glob("*")) if p.suffix.lower() in EXTS]


@app.get("/api/cases", response_model=list[CaseSummary])
def cases():
    return store.list_cases()


@app.get("/api/cases/{case_id}", response_model=AnalysisResult)
def case(case_id: str):
    return _get(case_id)


@app.post("/api/cases/{case_id}/review", response_model=AnalysisResult)
def review(case_id: str, body: ReviewIn):
    _get(case_id)
    return store.review(case_id, body.decision, body.note)


@app.get("/api/cases/{case_id}/report", response_class=HTMLResponse)
def case_report(case_id: str):
    return report.render(_get(case_id))


@app.get("/api/audit")
def audit(case_id: str | None = None):
    return store.audit(case_id)


@app.get("/api/metrics")
def metrics():
    p = STATIC / "metrics.json"
    if not p.exists():
        raise HTTPException(404, "metrics.json not generated yet (run scripts/eval.py)")
    return json.loads(p.read_text(encoding="utf-8"))
