"""
signals/metadata_pdf.py

Renders a build_metadata_report() dict (from signals/metadata.py) into a
professional-looking forensic PDF report using ReportLab.

This module only formats data that was already extracted elsewhere; it
never invents a value. Missing fields are rendered as "N/A". GPS/location
information is included only when the report says GPS was actually
present, and the map image is embedded only if one was actually generated.

Public entry point: generate_metadata_pdf(image_path, metadata_report, output_path)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FORENSIC_NOTICE = (
    "Metadata values shown in this report are extracted from the submitted "
    "file. Missing metadata does not establish authenticity or manipulation. "
    "GPS-derived locations are approximate and depend on the metadata and "
    "geocoding source."
)

_TABLE_STYLE = TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
])

_HASH_TABLE_STYLE = TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("FONTSIZE", (1, 0), (1, -1), 7.5),
    ("FONTNAME", (1, 0), (1, -1), "Courier"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
])


def _fmt(value) -> str:
    if value is None or value == "":
        return "N/A"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


_CELL_STYLE = ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, leading=11)


def _dict_table(data: dict, col_widths=(2.2 * inch, 3.8 * inch), style=_TABLE_STYLE, wrap_values=True) -> Table:
    rows = []
    for label, value in data.items():
        text = _fmt(value)
        # Wrap long strings (e.g. a full reverse-geocoded address) in a
        # Paragraph so they reflow inside the cell instead of overflowing
        # the page; short values/hashes are left as plain strings.
        cell = Paragraph(text, _CELL_STYLE) if wrap_values and len(text) > 40 else text
        rows.append([label, cell])
    if not rows:
        rows = [["(none)", "N/A"]]
    table = Table(rows, colWidths=list(col_widths))
    table.setStyle(style)
    return table


def generate_metadata_pdf(image_path: str, metadata_report: dict, output_path: str) -> str:
    """
    Build a forensic metadata PDF report at `output_path` from a dict
    produced by signals.metadata.build_metadata_report(). Returns the
    saved path.
    """

    path = Path(image_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"],
        spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1a1a2e"),
    )
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], textColor=colors.HexColor("#0f0f1a"),
    )
    body_style = styles["BodyText"]
    notice_style = ParagraphStyle(
        "Notice", parent=styles["BodyText"], fontSize=8,
        textColor=colors.HexColor("#555555"), borderPadding=6,
    )

    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title="Forensic Image Metadata Report",
    )

    story = []

    # --- Title ---
    story.append(Paragraph("FORENSIC IMAGE METADATA REPORT", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Image:</b> {path.name}", body_style))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph(f"<b>Generated:</b> {generated_at}", body_style))
    story.append(Spacer(1, 6))

    # --- File information ---
    story.append(Paragraph("FILE INFORMATION", heading_style))
    story.append(_dict_table(metadata_report.get("file") or {}))

    # --- Image / JPEG information ---
    story.append(Paragraph("IMAGE / JPEG INFORMATION", heading_style))
    image_info = {}
    image_info.update(metadata_report.get("composite") or {})
    if metadata_report.get("jpeg"):
        image_info.update(metadata_report["jpeg"])
    if metadata_report.get("jfif"):
        image_info.update(metadata_report["jfif"])
    story.append(_dict_table(image_info))

    # --- EXIF information ---
    story.append(Paragraph("EXIF INFORMATION", heading_style))
    exif = metadata_report.get("exif") or {}
    if "error" in exif:
        story.append(Paragraph("No EXIF metadata found in this file.", body_style))
    else:
        story.append(_dict_table(exif))

    # --- GPS / Location ---
    story.append(Paragraph("GPS / LOCATION", heading_style))
    gps = metadata_report.get("gps") or {"present": False}

    if not gps.get("present"):
        story.append(Paragraph("No GPS location metadata was found in this image.", body_style))
    else:
        story.append(Paragraph(
            "This information is interpreted from the GPS metadata. Locations are "
            "approximate and may not represent the exact position.",
            body_style,
        ))
        story.append(Spacer(1, 4))

        loc = gps.get("location") or {}
        location_str = "N/A"
        address_str = "N/A"
        if loc.get("available"):
            location_str = ", ".join(v for v in [loc.get("city"), loc.get("state"), loc.get("country")] if v) or "N/A"
            address_str = loc.get("display_name") or "N/A"

        gps_rows = {
            "Coordinates (Lat, Lon)": f"{gps['latitude']:.6f}, {gps['longitude']:.6f}",
            "Altitude": gps.get("altitude"),
            "GPS Timestamp": gps.get("timestamp"),
            "Approximate Location": location_str,
            "Approximate Range": "Unspecified",
            "Approximate Address": address_str,
        }
        story.append(_dict_table(gps_rows))

        map_path = gps.get("map_path")
        if map_path and Path(map_path).exists():
            story.append(Spacer(1, 8))
            story.append(RLImage(map_path, width=5.5 * inch, height=3.6 * inch))
        else:
            story.append(Spacer(1, 6))
            story.append(Paragraph("(Map image unavailable.)", body_style))

    # --- Digest / File integrity ---
    story.append(Paragraph("DIGEST / FILE INTEGRITY", heading_style))
    digest = metadata_report.get("digest") or {}
    digest_rows = {
        "MD5": digest.get("md5"),
        "SHA1": digest.get("sha1"),
        "SHA256": digest.get("sha256"),
    }
    story.append(_dict_table(digest_rows, col_widths=(1.3 * inch, 4.7 * inch), style=_HASH_TABLE_STYLE))

    # --- Forensic notice ---
    story.append(Spacer(1, 16))
    story.append(Paragraph("FORENSIC NOTICE", heading_style))
    story.append(Paragraph(FORENSIC_NOTICE, notice_style))

    doc.build(story)

    return str(out_path)
