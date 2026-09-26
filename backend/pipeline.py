"""analyze_image(path) -> AnalysisResult. Image-only. Each signal is isolated: one failure never crashes."""
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from backend import face as face_mod, fusion, narrator
from backend.schemas import AnalysisResult, Robustness, Signal
from backend.signals import classifier, ela, fft, metadata, noise

log = logging.getLogger("unmask")
STATIC = Path(__file__).parent / "static"
DISCLAIMER = ("Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. "
              "Final decision rests with a human reviewer.")
BAND_TEXT = {"clean": "No strong manipulation indicators found",
             "inconclusive": "Inconclusive — human review required",
             "strong": "Strong manipulation indicators — human review required"}
SIGNALS = [("classifier", classifier), ("ela", ela), ("fft", fft), ("noise", noise), ("metadata", metadata)]


def url(p: Path) -> str:
    """Root-relative static URL so the phone client can prefix its own backend base."""
    return "/static/" + p.relative_to(STATIC).as_posix()


def _timed(timings: dict, key: str, fn, *args):
    t = time.perf_counter()
    try:
        return fn(*args)
    finally:
        timings[key] = round((time.perf_counter() - t) * 1000, 1)
        log.info("%s %.1f ms", key, timings[key])


def _run_signal(sid: str, mod, img, face, case_dir: Path, timings: dict) -> Signal:
    try:
        return _timed(timings, sid, mod.run, img, face, case_dir)
    except Exception as e:  # noqa: BLE001
        log.exception("signal %s failed", sid)
        return Signal(id=sid, name=sid, score=0.0, reason="Signal unavailable.", ok=False, error=str(e))


def _overlay(img: np.ndarray, face, case_dir: Path) -> Path:
    """Placeholder heatmap (jaw band) until classifier.py provides the occlusion heatmap."""
    heat = np.zeros(img.shape[:2], np.float32)
    if face:
        x, y, w, h = face.box
        cv2.ellipse(heat, (x + w // 2, y + int(h * 0.75)), (w // 2, h // 4), 0, 0, 360, 1.0, -1)
    heat = cv2.GaussianBlur(heat, (0, 0), max(3, img.shape[1] // 30))
    cm = cv2.applyColorMap((heat / (heat.max() + 1e-6) * 255).astype(np.uint8), cv2.COLORMAP_JET)
    out = case_dir / "overlay.png"
    cv2.imwrite(str(out), cv2.addWeighted(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), 0.55, cm, 0.45, 0))
    return out


def _features(signals: list[Signal]) -> dict[str, float]:
    feats: dict[str, float] = {}
    for s in signals:
        if not s.ok:
            continue
        if s.id == "classifier":
            d = s.details or {}
            feats["cf"] = float(d.get("cf", s.score))
            feats["probe"] = float(d.get("probe", s.score))
        else:
            feats[s.id] = s.score
    return feats


def analyze_image(path: Path, case_id: str, sha256: str, filename: str) -> AnalysisResult:
    case_dir = path.parent
    timings: dict[str, float] = {}
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise ValueError("Could not decode image")
    img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    limitations: list[str] = []
    try:
        face = _timed(timings, "face", face_mod.detect, img)
    except Exception:  # noqa: BLE001
        log.exception("face detection failed")
        face = None
    if face is None:
        limitations.append("No face found; signals ran on the whole image.")
    elif min(face.box[2], face.box[3]) < 128:
        limitations.append("Face is smaller than 128 px (common on ID-card scans); reliability is reduced.")

    signals = [_run_signal(sid, mod, img, face, case_dir, timings) for sid, mod in SIGNALS]

    p, contrib = fusion.fuse(_features(signals))
    for s in signals:
        keys = ["cf", "probe"] if s.id == "classifier" else [s.id]
        s.contribution = round(sum(contrib.get(k, 0.0) for k in keys), 4)
        s.weight = round(sum(fusion.WEIGHTS.get(k, 0.0) for k in keys), 4)
    band = fusion.band(p)

    try:
        regions = classifier.region_scores(None, face.masks if face else {})
    except Exception:  # noqa: BLE001
        log.exception("region scoring failed")
        regions = []
    top = max(regions, key=lambda r: r.suspicion) if regions else None
    headline = (f"Suspicion concentrated at {top.region.replace('_', ' ')}"
                if top and band != "clean" else BAND_TEXT[band])

    try:
        overlay = url(_timed(timings, "overlay", _overlay, img, face, case_dir))
    except Exception:  # noqa: BLE001
        log.exception("overlay failed")
        overlay = url(path)

    s1 = next((s for s in signals if s.id == "classifier" and s.ok), None)
    robustness = Robustness(jpeg50=s1.score if s1 else 0.0, resize50=s1.score if s1 else 0.0)

    return AnalysisResult(
        case_id=case_id, sha256=sha256, filename=filename, created_at=datetime.now(timezone.utc).isoformat(),
        original=url(path), overlay=overlay, fused_score=round(p, 4), band=band, headline=headline,
        signals=signals, regions=regions, robustness=robustness,
        explanation=narrator.explain(headline, band, signals, limitations),
        limitations=limitations, disclaimer=DISCLAIMER, timings_ms=timings)
