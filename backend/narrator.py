"""Explanation text from result JSON only (LLM + template fallback). OWNER: Yadnesh. STUB: template."""


def explain(headline: str, band: str, signals: list, limitations: list[str]) -> str:
    top = sorted([s for s in signals if s.ok], key=lambda s: s.score, reverse=True)[:2]
    parts = "; ".join(f"{s.name}: {s.reason}" for s in top)
    return (f"{headline}. Main indicators: {parts} "
            "These are probabilistic indicators; a human reviewer makes the final decision.")
