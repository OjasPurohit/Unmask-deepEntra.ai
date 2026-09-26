"""
signals/map.py

Renders a static map image centered on a coordinate, for GPS metadata that
was actually extracted from an image's embedded EXIF (never called for a
location inferred any other way). Uses the `staticmap` library, which
composes public OpenStreetMap tiles client-side (no API key needed for a
prototype); a network/tile failure returns None rather than raising.

Public entry point: generate_location_map(latitude, longitude, output_path, zoom=15)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

USER_AGENT = (
    "VeritasLens-ForensicPrototype/0.1 "
    "(+https://github.com/OjasPurohit/DeepEntra-Build-Fest-Masons-CYB-03)"
)

MARKER_COLOR = "#e6194b"
MAP_WIDTH = 640
MAP_HEIGHT = 420


def generate_location_map(
    latitude: float,
    longitude: float,
    output_path: str,
    zoom: int = 15,
) -> Optional[str]:
    """
    Render a map centered on (latitude, longitude) with a marker, and save
    it to `output_path`. Returns the saved path, or None if the map could
    not be generated (network failure, tile server unavailable, etc.) --
    this must never crash the forensic pipeline.
    """

    try:
        from staticmap import CircleMarker, StaticMap

        m = StaticMap(
            MAP_WIDTH,
            MAP_HEIGHT,
            url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
            headers={"User-Agent": USER_AGENT},
            tile_request_timeout=8,
        )

        # staticmap takes (lon, lat) coordinate order.
        marker = CircleMarker((longitude, latitude), MARKER_COLOR, 14)
        m.add_marker(marker)

        image = m.render(zoom=zoom)

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(out_path)

        return str(out_path)

    except Exception:
        # Tile server unreachable, rate-limited, or any other rendering
        # failure: the report still works, it just has no map image.
        return None
