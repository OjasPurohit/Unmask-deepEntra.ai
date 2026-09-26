"""Printable KYC evidence report HTML for GET /api/cases/{id}/report. OWNER: Yadnesh. STUB."""
import html

from backend.schemas import AnalysisResult


def render(r: AnalysisResult) -> str:
    e = html.escape
    rows = "".join(f"<tr><td>{e(s.name)}</td><td>{s.score:.2f}</td><td>{e(s.reason)}</td></tr>" for s in r.signals)
    lims = "".join(f"<li>{e(x)}</li>" for x in r.limitations)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>KYC Verification Evidence Report</title></head>
<body style="font-family:sans-serif;max-width:800px;margin:auto">
<h1>KYC Verification Evidence Report</h1>
<p>Case {r.case_id} · {e(r.filename)} · SHA-256 {r.sha256}</p>
<h2>{r.band.upper()} · {r.fused_score:.0%}</h2><p>{e(r.headline)}</p>
<img src="{r.overlay}" style="max-width:100%">
<table border="1" cellpadding="4">{rows}</table>
<p>{e(r.explanation)}</p><ul>{lims}</ul>
<p><b>{e(r.disclaimer)}</b></p></body></html>"""
