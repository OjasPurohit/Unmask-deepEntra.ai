"""
signals/metadata.py

Image metadata analysis.

Reports what is actually present in the file's EXIF/format metadata:
camera make/model, software tag, timestamps, dimensions, format, color
mode, and a lightweight check for a C2PA/JUMBF provenance marker. It
does NOT assume "Photoshop in the Software tag = fake" or "missing EXIF
= fake" — both are extremely common in ordinary, unmanipulated images
(re-encoded by messaging apps, screenshotted, exported from a phone's
gallery app, etc.). This score is conservative and low-weight by design;
metadata is supporting evidence only.

Metadata requires the original file bytes, so this module needs
`image_path` (a bare pixel array/PIL Image with no path has no EXIF to
read); if only `image` is given with no path, the score is reported as
None rather than fabricated.

Public entry point: analyze(image=None, image_path=None, output_dir=None)
"""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import ExifTags, Image

from signals._util import clip_score, error_result

# Software tag substrings that indicate an editing/generation tool was
# involved at some point. Presence is reported as a fact, not treated as
# proof of manipulation — plenty of legitimately edited real photos carry
# these tags too (cropping, color-correcting, watermarking a real photo).
SUSPICIOUS_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "lightroom", "affinity",
    "stable diffusion", "midjourney", "dall-e", "dalle",
    "comfyui", "stability", "leonardo.ai", "imagen", "firefly",
    "diffusers", "automatic1111",
]

# Engineering defaults, not scientifically calibrated (see module docstring).
SOFTWARE_TAG_SCORE = 0.35
MISSING_EXIF_SCORE = 0.15
EXIF_NO_CAMERA_SCORE = 0.05
C2PA_MARKER_SCORE = 0.0  # presence alone is not suspicious; reported as a fact only


def _readable_exif(image: Image.Image) -> dict:
    exif = image.getexif()
    tags = {}
    for tag_id, value in exif.items():
        name = ExifTags.TAGS.get(tag_id, str(tag_id))
        try:
            if isinstance(value, bytes):
                value = value.decode(errors="replace")
            tags[name] = value
        except Exception:
            continue
    return tags


def _check_c2pa_marker(path: Path, max_bytes: int = 4_000_000) -> bool:
    """
    Heuristic only: look for the 'jumb'/'C2PA' byte sequences a JUMBF/C2PA
    provenance manifest embeds. A false negative is likely for manifests
    stored differently; this does not claim to be a full C2PA parser.
    """

    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return b"jumb" in data.lower() or b"c2pa" in data.lower()
    except Exception:
        return False


# ============================================================
# ExifTool-style file / JPEG / JFIF / composite report
# ============================================================

_CANONICAL_EXTENSION = {
    "JPEG": "jpg", "PNG": "png", "BMP": "bmp", "GIF": "gif",
    "TIFF": "tif", "WEBP": "webp",
}

_MIME_BY_FORMAT = {
    "JPEG": "image/jpeg", "PNG": "image/png", "BMP": "image/bmp",
    "GIF": "image/gif", "TIFF": "image/tiff", "WEBP": "image/webp",
}

# JPEG SOFn marker byte -> human-readable encoding process. Excludes
# 0xC4 (DHT), 0xC8 (JPG reserved) and 0xCC (DAC), which are not SOF markers.
_SOF_ENCODING_PROCESS = {
    0xC0: "Baseline DCT, Huffman coding",
    0xC1: "Extended sequential DCT, Huffman coding",
    0xC2: "Progressive DCT, Huffman coding",
    0xC3: "Lossless, Huffman coding",
    0xC5: "Differential sequential DCT, Huffman coding",
    0xC6: "Differential progressive DCT, Huffman coding",
    0xC7: "Differential lossless, Huffman coding",
    0xC9: "Extended sequential DCT, Arithmetic coding",
    0xCA: "Progressive DCT, Arithmetic coding",
    0xCB: "Lossless, Arithmetic coding",
    0xCD: "Differential sequential DCT, Arithmetic coding",
    0xCE: "Differential progressive DCT, Arithmetic coding",
    0xCF: "Differential lossless, Arithmetic coding",
}

_CHROMA_SUBSAMPLING = {
    (1, 1): "4:4:4", (2, 1): "4:2:2", (1, 2): "4:4:0",
    (2, 2): "4:2:0", (4, 1): "4:1:1",
}

_RESOLUTION_UNIT = {0: "None", 1: "inches", 2: "cm"}


def _parse_jpeg_segments(data: bytes) -> dict:
    """
    Minimal JPEG marker scanner over the ORIGINAL file bytes: finds the
    first SOFn (Start Of Frame) segment (encoding process, bit depth,
    component/subsampling info) and the JFIF APP0 segment if present.
    Returns {"sof": dict | None, "jfif": dict | None}. Never raises;
    a malformed/truncated JPEG just yields fewer fields, not a crash.
    """

    result = {"sof": None, "jfif": None}

    try:
        n = len(data)
        if n < 4 or data[0:2] != b"\xff\xd8":
            return result

        i = 2
        while i < n - 1:
            if data[i] != 0xFF:
                i += 1
                continue

            j = i + 1
            while j < n and data[j] == 0xFF:
                j += 1
            if j >= n:
                break

            marker = data[j]
            i = j + 1

            # Markers with no length field.
            if marker in (0xD8, 0x01) or (0xD0 <= marker <= 0xD7):
                continue
            if marker == 0xD9:  # EOI
                break
            if i + 2 > n:
                break

            seg_len = (data[i] << 8) | data[i + 1]
            seg_start = i + 2
            seg_end = min(i + seg_len, n)
            payload = data[seg_start:seg_end]

            if marker == 0xE0 and payload[:5] == b"JFIF\x00" and len(payload) >= 12 and result["jfif"] is None:
                major, minor, units = payload[5], payload[6], payload[7]
                x_density = (payload[8] << 8) | payload[9]
                y_density = (payload[10] << 8) | payload[11]
                result["jfif"] = {
                    "version_major": major,
                    "version_minor": minor,
                    "units": units,
                    "x_density": x_density,
                    "y_density": y_density,
                }

            if marker in _SOF_ENCODING_PROCESS and result["sof"] is None and len(payload) >= 6:
                precision = payload[0]
                height = (payload[1] << 8) | payload[2]
                width = (payload[3] << 8) | payload[4]
                num_components = payload[5]
                components = []
                idx = 6
                for _ in range(num_components):
                    if idx + 3 > len(payload):
                        break
                    comp_id = payload[idx]
                    hv = payload[idx + 1]
                    components.append({"id": comp_id, "h": (hv >> 4) & 0xF, "v": hv & 0xF})
                    idx += 3
                result["sof"] = {
                    "marker": marker,
                    "precision": precision,
                    "height": height,
                    "width": width,
                    "num_components": num_components,
                    "components": components,
                }

            if marker == 0xDA:  # SOS: compressed data follows, stop scanning headers
                break

            i = seg_end

    except Exception:
        pass  # a malformed header just yields fewer fields, never a crash

    return result


def build_file_report(image_path: str) -> dict:
    """
    Build an ExifTool-style file/JPEG/JFIF/composite report from
    `image_path`, using Pillow for dimensions/mode and a raw byte scan
    for JPEG-specific SOF/JFIF fields. Missing fields are None (the
    terminal report prints those as "N/A"; a frontend can treat them
    as absent). Never raises for a supported image; returns partial
    data with an "error" key if the file truly can't be opened.
    """

    path = Path(image_path)

    try:
        raw_bytes = path.read_bytes()
        pil_image = Image.open(path)
        pil_image.load()  # ensure fully decoded before reading size/bands

        image_format = pil_image.format
        rgb_image = pil_image.convert("RGB")
        unique_colors = None
        try:
            colors = rgb_image.getcolors(maxcolors=rgb_image.width * rgb_image.height)
            if colors is not None:
                unique_colors = len(colors)
        except Exception:
            unique_colors = None

        file_section = {
            "Filename": path.name,
            "File Type": image_format,
            "File Type Extension": _CANONICAL_EXTENSION.get(image_format, path.suffix.lstrip(".").lower() or None),
            "MIME Type": _MIME_BY_FORMAT.get(image_format) or mimetypes.guess_type(str(path))[0],
            "Image Width": pil_image.width,
            "Image Height": pil_image.height,
            "Color Channels": len(pil_image.getbands()),
            "Unique Colors": unique_colors,
            "File Size": len(raw_bytes),
        }

        jpeg_section = None
        jfif_section = None

        if image_format == "JPEG":
            segments = _parse_jpeg_segments(raw_bytes)
            sof = segments["sof"]
            jfif = segments["jfif"]

            if sof is not None:
                subsampling = None
                if sof["num_components"] >= 3 and sof["components"]:
                    y_comp = sof["components"][0]
                    ratio = _CHROMA_SUBSAMPLING.get((y_comp["h"], y_comp["v"]))
                    if ratio is not None:
                        subsampling = f"YCbCr{ratio} ({y_comp['h']} {y_comp['v']})"

                jpeg_section = {
                    "Encoding Process": _SOF_ENCODING_PROCESS.get(sof["marker"]),
                    "Bits Per Sample": sof["precision"],
                    "Color Components": sof["num_components"],
                    "Y Cb Cr Sub Sampling": subsampling,
                }

            if jfif is not None:
                jfif_section = {
                    "JFIF Version": f"{jfif['version_major']}.{jfif['version_minor']:02d}",
                    "Resolution Unit": _RESOLUTION_UNIT.get(jfif["units"], "Unknown"),
                    "X Resolution": jfif["x_density"],
                    "Y Resolution": jfif["y_density"],
                }

        megapixels = round((pil_image.width * pil_image.height) / 1_000_000, 3)
        composite_section = {
            "Image Size": f"{pil_image.width}x{pil_image.height}",
            "Megapixels": megapixels,
        }

        return {
            "file": file_section,
            "jpeg": jpeg_section,
            "jfif": jfif_section,
            "composite": composite_section,
        }

    except Exception as exc:
        return {"file": None, "jpeg": None, "jfif": None, "composite": None, "error": f"{type(exc).__name__}: {exc}"}


def build_digest_report(image_path: str) -> dict:
    """
    Build the file-integrity digest: filename, file size, MD5/SHA1/SHA256
    over the ORIGINAL file bytes (never the decoded/re-encoded pixels),
    and the current UTC timestamp this analysis ran at.
    """

    path = Path(image_path)

    try:
        raw_bytes = path.read_bytes()

        return {
            "Filename": path.name,
            "File Size": len(raw_bytes),
            "MD5": hashlib.md5(raw_bytes).hexdigest(),
            "SHA1": hashlib.sha1(raw_bytes).hexdigest(),
            "SHA256": hashlib.sha256(raw_bytes).hexdigest(),
            "First Analyzed": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fmt(value) -> str:
    """Render a report value for the terminal: None -> N/A, int -> thousands-separated."""

    if value is None:
        return "N/A"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _print_section(title: str, fields: dict, suffix: dict = None) -> None:
    print(f"\n{title}")
    print("-" * 60)
    for label, value in fields.items():
        text = _fmt(value)
        if suffix and label in suffix:
            text = f"{text} {suffix[label]}"
        print(f"{label:<23}{text}")


def print_metadata_report(image_path: str) -> dict:
    """
    Print the full ExifTool-style metadata + digest report for
    `image_path` to stdout, and return the same data as a dict:
    {"file_report": {...}, "digest_report": {...}}.
    """

    file_report = build_file_report(image_path)
    digest_report = build_digest_report(image_path)

    print("=" * 60)
    print("METADATA ANALYSIS")
    print("=" * 60)

    if file_report.get("file") is None:
        print(f"\n(unable to read file report: {file_report.get('error', 'unknown error')})")
    else:
        byte_suffix = {"File Size": "bytes"}
        _print_section("File", file_report["file"], suffix=byte_suffix)

        if file_report.get("jpeg") is not None:
            _print_section("JPEG", file_report["jpeg"])

        if file_report.get("jfif") is not None:
            _print_section("JFIF", file_report["jfif"])

        if file_report.get("composite") is not None:
            _print_section("Composite", file_report["composite"])

    print("\n" + "=" * 60)
    print("DIGEST / FILE INTEGRITY")
    print("=" * 60)

    if "error" in digest_report:
        print(f"\n(unable to compute digest: {digest_report['error']})")
    else:
        byte_suffix = {"File Size": "bytes"}
        _print_section("Digest", digest_report, suffix=byte_suffix)

    print("\n" + "=" * 60)

    return {"file_report": file_report, "digest_report": digest_report}


# ============================================================
# Comprehensive EXIF + GPS extraction, reverse geocoding, map, report
# ============================================================

# Standard EXIF value tables (documented in the EXIF 2.3 spec / matched by
# exiftool's own output wording) -- used only to translate a numeric code
# that IS present in the file into its human-readable meaning. A code not
# in a table is shown as "Unknown (code N)", never guessed.
_FLASH_VALUES = {
    0x0: "No Flash", 0x1: "Fired", 0x5: "Fired, Return not detected",
    0x7: "Fired, Return detected", 0x8: "On, Did not fire",
    0x9: "Fired, Compulsory", 0xD: "Fired, Compulsory, Return not detected",
    0xF: "Fired, Compulsory, Return detected", 0x10: "Did not fire, Compulsory",
    0x18: "Did not fire, Auto", 0x19: "Fired, Auto",
    0x1D: "Fired, Auto, Return not detected", 0x1F: "Fired, Auto, Return detected",
    0x20: "No flash function", 0x41: "Fired, Red-eye reduction",
    0x45: "Fired, Red-eye reduction, Return not detected",
    0x47: "Fired, Red-eye reduction, Return detected",
    0x49: "Fired, Compulsory, Red-eye reduction",
    0x4D: "Fired, Compulsory, Red-eye reduction, Return not detected",
    0x4F: "Fired, Compulsory, Red-eye reduction, Return detected",
    0x59: "Fired, Auto, Red-eye reduction",
}
_EXPOSURE_PROGRAM_VALUES = {
    0: "Not Defined", 1: "Manual", 2: "Program AE", 3: "Aperture priority",
    4: "Shutter priority", 5: "Creative", 6: "Action", 7: "Portrait", 8: "Landscape",
}
_METERING_MODE_VALUES = {
    0: "Unknown", 1: "Average", 2: "Center-weighted average", 3: "Spot",
    4: "Multi-spot", 5: "Multi-segment", 6: "Partial", 255: "Other",
}
_WHITE_BALANCE_VALUES = {0: "Auto", 1: "Manual"}
_ORIENTATION_VALUES = {
    1: "Horizontal (normal)", 2: "Mirror horizontal", 3: "Rotate 180",
    4: "Mirror vertical", 5: "Mirror horizontal and rotate 270 CW",
    6: "Rotate 90 CW", 7: "Mirror horizontal and rotate 90 CW", 8: "Rotate 270 CW",
}
_SCENE_CAPTURE_TYPE_VALUES = {0: "Standard", 1: "Landscape", 2: "Portrait", 3: "Night"}
_COLOR_SPACE_VALUES = {1: "sRGB", 2: "Adobe RGB", 65535: "Uncalibrated"}
_GPS_ALTITUDE_REF_VALUES = {0: "Above Sea Level", 1: "Below Sea Level"}


def _decode(value):
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _rational_to_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_exposure_time(value) -> Optional[str]:
    f = _rational_to_float(value)
    if f is None:
        return None
    if 0 < f < 1:
        return f"1/{round(1 / f)}"
    return str(f)


def _extract_ifds(pil_image: Image.Image) -> tuple:
    """
    Pull the 0th IFD, the Exif sub-IFD and the GPS sub-IFD from a PIL
    image's EXIF block, each as {tag_name: value}. Any IFD that isn't
    present (or fails to parse) comes back as an empty dict -- never
    fabricated, never crashes the caller.
    """

    base_tags = {}
    exif_tags = {}
    gps_tags = {}

    try:
        exif = pil_image.getexif()

        for tag_id, value in exif.items():
            base_tags[ExifTags.TAGS.get(tag_id, str(tag_id))] = _decode(value)

        try:
            exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
            for tag_id, value in exif_ifd.items():
                exif_tags[ExifTags.TAGS.get(tag_id, str(tag_id))] = _decode(value)
        except Exception:
            pass

        try:
            gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
            for tag_id, value in gps_ifd.items():
                gps_tags[ExifTags.GPSTAGS.get(tag_id, str(tag_id))] = value
        except Exception:
            pass

    except Exception:
        pass

    return base_tags, exif_tags, gps_tags


def build_exif_report(pil_image: Image.Image) -> dict:
    """
    Comprehensive, human-readable EXIF field extraction (camera, exposure,
    lens, timestamps, etc.), separate from GPS. Every field is None if the
    file simply doesn't carry that tag -- nothing here is invented.
    """

    base_tags, exif_tags, _ = _extract_ifds(pil_image)
    merged = {**base_tags, **exif_tags}  # Exif sub-IFD wins on overlapping names

    flash_raw = merged.get("Flash")
    exposure_program_raw = merged.get("ExposureProgram")
    metering_mode_raw = merged.get("MeteringMode")
    white_balance_raw = merged.get("WhiteBalance")
    orientation_raw = merged.get("Orientation")
    scene_capture_raw = merged.get("SceneCaptureType")
    color_space_raw = merged.get("ColorSpace")

    return {
        "DateTime": merged.get("DateTime"),
        "DateTimeOriginal": merged.get("DateTimeOriginal"),
        "DateTimeDigitized": merged.get("DateTimeDigitized"),
        "Make": merged.get("Make"),
        "Model": merged.get("Model"),
        "Software": merged.get("Software"),
        "LensMake": merged.get("LensMake"),
        "LensModel": merged.get("LensModel"),
        "FNumber": _rational_to_float(merged.get("FNumber")),
        "ExposureTime": _format_exposure_time(merged.get("ExposureTime")),
        "ISOSpeedRatings": merged.get("ISOSpeedRatings") or merged.get("PhotographicSensitivity"),
        "FocalLength": _rational_to_float(merged.get("FocalLength")),
        "Flash": _FLASH_VALUES.get(flash_raw, f"Unknown (code {flash_raw})" if flash_raw is not None else None),
        "WhiteBalance": _WHITE_BALANCE_VALUES.get(white_balance_raw, f"Unknown (code {white_balance_raw})" if white_balance_raw is not None else None),
        "ExposureProgram": _EXPOSURE_PROGRAM_VALUES.get(exposure_program_raw, f"Unknown (code {exposure_program_raw})" if exposure_program_raw is not None else None),
        "MeteringMode": _METERING_MODE_VALUES.get(metering_mode_raw, f"Unknown (code {metering_mode_raw})" if metering_mode_raw is not None else None),
        "Orientation": _ORIENTATION_VALUES.get(orientation_raw, f"Unknown (code {orientation_raw})" if orientation_raw is not None else None),
        "SceneCaptureType": _SCENE_CAPTURE_TYPE_VALUES.get(scene_capture_raw, f"Unknown (code {scene_capture_raw})" if scene_capture_raw is not None else None),
        "ColorSpace": _COLOR_SPACE_VALUES.get(color_space_raw, f"Unknown (code {color_space_raw})" if color_space_raw is not None else None),
        "PixelXDimension": merged.get("PixelXDimension"),
        "PixelYDimension": merged.get("PixelYDimension"),
    }


def _dms_to_decimal(dms, ref) -> Optional[float]:
    """Convert an EXIF (degrees, minutes, seconds) tuple + N/S/E/W ref to decimal degrees."""

    try:
        degrees, minutes, seconds = (float(v) for v in dms)
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except (TypeError, ValueError, IndexError):
        return None


def build_gps_report(pil_image: Image.Image, map_output_path: Optional[str] = None) -> dict:
    """
    Extract real embedded GPS metadata (never inferred from image content),
    convert to decimal coordinates, and -- only when coordinates were
    actually found -- reverse-geocode them and render a location map.

    Returns {"present": False, ...all-None...} when there is no usable GPS
    block, so downstream code never has to guess whether GPS was found.
    """

    _, _, gps_tags = _extract_ifds(pil_image)

    empty = {
        "present": False,
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "timestamp": None,
        "location": None,
        "map_path": None,
    }

    if not gps_tags:
        return empty

    latitude = _dms_to_decimal(gps_tags.get("GPSLatitude"), gps_tags.get("GPSLatitudeRef"))
    longitude = _dms_to_decimal(gps_tags.get("GPSLongitude"), gps_tags.get("GPSLongitudeRef"))

    if latitude is None or longitude is None:
        return empty  # GPS IFD present but no usable coordinates -- not fabricated

    altitude = _rational_to_float(gps_tags.get("GPSAltitude"))
    altitude_ref_raw = gps_tags.get("GPSAltitudeRef")
    # GPSAltitudeRef is a single-byte EXIF field; Pillow can hand it back
    # as an int or as raw bytes (e.g. b'\x00') depending on how it was
    # written, so normalize before comparing.
    if isinstance(altitude_ref_raw, bytes):
        altitude_ref = altitude_ref_raw[0] if altitude_ref_raw else None
    else:
        altitude_ref = altitude_ref_raw
    if altitude is not None and altitude_ref == 1:
        altitude = -altitude

    timestamp = None
    time_parts = gps_tags.get("GPSTimeStamp")
    date_stamp = gps_tags.get("GPSDateStamp")
    if time_parts is not None:
        try:
            h, m, s = (int(_rational_to_float(v) or 0) for v in time_parts)
            timestamp = f"{date_stamp or ''} {h:02d}:{m:02d}:{s:02d} UTC".strip()
        except Exception:
            timestamp = date_stamp

    location = None
    try:
        from signals.geolocation import reverse_geocode
        location = reverse_geocode(latitude, longitude)
    except Exception as exc:
        location = {"available": False, "error": f"{type(exc).__name__}: {exc}"}

    map_path = None
    if map_output_path is not None:
        try:
            from signals.map import generate_location_map
            map_path = generate_location_map(latitude, longitude, map_output_path)
        except Exception:
            map_path = None

    return {
        "present": True,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "timestamp": timestamp,
        "location": location,
        "map_path": map_path,
    }


def build_metadata_report(image_path: str, map_output_dir: Optional[str] = None) -> dict:
    """
    The full, frontend-ready forensic metadata report: file/JPEG/JFIF/
    composite (reusing build_file_report), comprehensive EXIF, GPS +
    reverse-geocoded location + map (only when GPS metadata truly exists),
    and the file-integrity digest. Fully JSON-serializable.
    """

    path = Path(image_path)
    file_report = build_file_report(image_path)
    digest = build_digest_report(image_path)

    exif_report = {}
    gps_report = {
        "present": False, "latitude": None, "longitude": None,
        "altitude": None, "timestamp": None, "location": None, "map_path": None,
    }

    try:
        pil_image = Image.open(path)
        pil_image.load()

        exif_report = build_exif_report(pil_image)

        map_output_path = None
        if map_output_dir is not None:
            map_output_path = str(Path(map_output_dir) / f"{path.stem}_location_map.png")

        gps_report = build_gps_report(pil_image, map_output_path)

    except Exception as exc:
        exif_report = {"error": f"{type(exc).__name__}: {exc}"}

    return {
        "file": file_report.get("file"),
        "jpeg": file_report.get("jpeg"),
        "jfif": file_report.get("jfif"),
        "composite": file_report.get("composite"),
        "exif": exif_report,
        "gps": gps_report,
        "digest": {
            "md5": digest.get("MD5"),
            "sha1": digest.get("SHA1"),
            "sha256": digest.get("SHA256"),
            "file_size": digest.get("File Size"),
            "first_analyzed": digest.get("First Analyzed"),
        },
    }


def print_forensic_report(image_path: str, map_output_dir: Optional[str] = None) -> dict:
    """
    Print the complete "FORENSIC METADATA REPORT" (File/JPEG/JFIF/
    Composite/EXIF/GPS/Digest) for `image_path`, and return the same data
    from build_metadata_report(). Generates a location map only if real
    GPS metadata was found.
    """

    report = build_metadata_report(image_path, map_output_dir=map_output_dir)

    print("=" * 60)
    print("FORENSIC METADATA REPORT")
    print("=" * 60)

    if report["file"] is not None:
        _print_section("FILE", report["file"], suffix={"File Size": "bytes"})
    if report["jpeg"] is not None:
        _print_section("JPEG", report["jpeg"])
    if report["jfif"] is not None:
        _print_section("JFIF", report["jfif"])
    if report["composite"] is not None:
        composite = dict(report["composite"])
        w_str, h_str = composite["Image Size"].split("x")
        w, h = int(w_str), int(h_str)
        from math import gcd
        g = gcd(w, h) or 1
        composite["Aspect Ratio"] = f"{w // g}:{h // g}  ({w / h:.3f})"
        _print_section("COMPOSITE", composite)

    print("\nEXIF")
    print("-" * 60)
    exif = report["exif"]
    if not exif or "error" in exif:
        print("N/A (no EXIF data found)")
    else:
        for label, value in exif.items():
            print(f"{label:<23}{_fmt(value)}")

    print("\nGPS")
    print("-" * 60)
    gps = report["gps"]
    if not gps["present"]:
        print("GPS Present:           No")
        print("\nGPS Location")
        print("No GPS location metadata was found in this image.")
    else:
        print("GPS Present:           Yes")
        print(f"Coordinates:           {gps['latitude']:.6f}, {gps['longitude']:.6f}")
        print(f"Altitude:              {_fmt(gps['altitude'])}")
        print(f"GPS Timestamp:         {_fmt(gps['timestamp'])}")

        print("\nApproximate GPS Location")
        print("This information is interpreted from the GPS metadata. Locations")
        print("are approximate and may not represent the exact position.")

        loc = gps["location"] or {}
        print(f"\nApproximate Coordinates: {gps['latitude']:.6f}, {gps['longitude']:.6f}")

        if loc.get("available"):
            city_state_country = ", ".join(v for v in [loc.get("city"), loc.get("state"), loc.get("country")] if v)
            print(f"Approximate Location:    {city_state_country or 'N/A'}")
            print(f"Approximate Range:       Unspecified")
            print(f"Approximate Address:     {loc.get('display_name') or 'N/A'}")
        else:
            print("Approximate Location:    N/A (reverse geocoding unavailable)")
            print("Approximate Range:       Unspecified")
            print("Approximate Address:     N/A (reverse geocoding unavailable)")

        if gps.get("map_path"):
            print(f"\nMap image saved to: {gps['map_path']}")

    print("\nDIGEST")
    print("-" * 60)
    digest = report["digest"]
    print(f"{'MD5:':<23}{_fmt(digest['md5'])}")
    print(f"{'SHA1:':<23}{_fmt(digest['sha1'])}")
    print(f"{'SHA256:':<23}{_fmt(digest['sha256'])}")

    print("\n" + "=" * 60)

    return report


def analyze(
    image: Optional[Union[Image.Image, np.ndarray]] = None,
    image_path: Optional[str] = None,
    output_dir: Optional[str] = None,  # accepted for interface consistency; unused (no visualization)
) -> dict:
    """
    Analyze image metadata.

    Returns:
        {"name": "Metadata", "score": float | None, "reason": str,
         "visualization": None, "details": dict}
    """

    if image_path is None:
        return {
            "name": "Metadata",
            "score": None,
            "reason": "No file path provided; metadata requires the original file bytes.",
            "visualization": None,
            "details": {"error": "image_path was not provided"},
        }

    try:
        path = Path(image_path)
        pil_image = Image.open(path)  # not .convert()'d, to keep .info/.getexif() intact

        exif_tags = _readable_exif(pil_image)
        has_exif = bool(exif_tags)

        camera_make = exif_tags.get("Make")
        camera_model = exif_tags.get("Model")
        software = exif_tags.get("Software")
        datetime_original = exif_tags.get("DateTimeOriginal") or exif_tags.get("DateTime")
        has_camera = bool(camera_make or camera_model)

        c2pa_marker_found = _check_c2pa_marker(path)

        score = 0.0
        reasons = []

        if software:
            software_lower = str(software).lower()
            if any(keyword in software_lower for keyword in SUSPICIOUS_SOFTWARE_KEYWORDS):
                score += SOFTWARE_TAG_SCORE
                reasons.append(f"Software tag '{software}' matches a known editing/generation tool")

        if not has_exif:
            score += MISSING_EXIF_SCORE
            reasons.append("No EXIF metadata found (common for screenshots, re-encoded, or web-downloaded images — not evidence on its own)")
        elif not has_camera:
            score += EXIF_NO_CAMERA_SCORE
            reasons.append("EXIF present but no camera make/model tag")

        if c2pa_marker_found:
            reasons.append("A C2PA/JUMBF-style provenance marker byte sequence was found in the file (presence noted, not interpreted)")

        score = clip_score(score)

        if not reasons:
            reason = "Standard camera EXIF metadata present (make/model found); no suspicious software tags detected."
        else:
            reason = "; ".join(reasons) + "."

        return {
            "name": "Metadata",
            "score": score,
            "reason": reason,
            "visualization": None,
            "details": {
                "format": pil_image.format,
                "mode": pil_image.mode,
                "size": [pil_image.width, pil_image.height],
                "has_exif": has_exif,
                "camera_make": camera_make,
                "camera_model": camera_model,
                "software": software,
                "datetime_original": datetime_original,
                "c2pa_marker_found": c2pa_marker_found,
                "exif_tags": {k: str(v) for k, v in exif_tags.items()},
                # Additive, structured ExifTool-style report + file-integrity
                # digest, for the terminal report and a future frontend/API.
                # Does not affect `score`/`reason` above in any way.
                "file_report": build_file_report(image_path),
                "digest": build_digest_report(image_path),
            },
        }

    except Exception as exc:  # a bad/corrupt image must not crash the pipeline
        return error_result("Metadata", exc)
