"""Fusion over [cf, probe, ela, fft, noise, metadata]. OWNER: Omkar. STUB: fixed weights."""
import math

FEATURES = ["cf", "probe", "ela", "fft", "noise", "metadata"]
WEIGHTS = {"cf": 2.0, "probe": 2.5, "ela": 1.0, "fft": 0.6, "noise": 1.2, "metadata": 0.3}
BIAS = -3.2


def fuse(scores: dict[str, float]) -> tuple[float, dict[str, float]]:
    contrib = {k: WEIGHTS[k] * scores[k] for k in FEATURES if k in scores}
    z = BIAS + sum(contrib.values())
    return 1 / (1 + math.exp(-z)), contrib


def band(p: float) -> str:
    return "clean" if p < 0.35 else ("inconclusive" if p <= 0.70 else "strong")
