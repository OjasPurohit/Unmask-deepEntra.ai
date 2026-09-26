"""
core/face.py

Face detection and facial-region extraction.

Responsibility of this module ONLY:
    - find a face in an image
    - return its 478 landmarks in pixel coordinates
    - build region masks/polygons (eyes, mouth, nose, jaw boundary, skin, background)

This module does NOT do deepfake classification, heatmaps, or fusion.
Those live in other modules (S1 ensemble, later signal modules).

Primary entry point:

    face_result = detect_face(image)

`image` may be a PIL.Image (any mode) or an RGB numpy array (H, W, 3), uint8.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from PIL import Image

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,
)


# ============================================================
# Standard MediaPipe FaceMesh (478-point) topology index sets
# ============================================================
#
# mediapipe's `tasks` API (used here) does not ship the old
# `mp.solutions.face_mesh` module, so the FACEMESH_* connection
# constants are not importable at runtime in this environment.
# The values below are the standard, publicly documented vertex
# indices for the FaceMesh topology (the same fixed topology used
# by face_landmarker.task), reproduced here as constants rather
# than invented from scratch.
#
# NOSE is not covered by an official FACEMESH_* connection set
# (MediaPipe only defines connections for lips, eyes, eyebrows,
# irises and the face oval). The NOSE_IDX set below is a small,
# commonly-used curated subset of nose-bridge/tip/wing landmarks,
# not an official MediaPipe constant. This is called out explicitly
# because it's the one region built without a standard reference set.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FACE_LANDMARKER_MODEL_PATH = PROJECT_ROOT / "models" / "face_landmarker.task"

NUM_LANDMARKS = 478

LEFT_EYE_IDX = [
    263, 249, 390, 373, 374, 380, 381, 382, 362,
    466, 388, 387, 386, 385, 384, 398,
]

RIGHT_EYE_IDX = [
    33, 7, 163, 144, 145, 153, 154, 155, 133,
    246, 161, 160, 159, 158, 157, 173,
]

LIPS_IDX = [
    # outer lip boundary
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
    409, 270, 269, 267, 0, 37, 39, 40, 185,
    # inner lip boundary
    78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308,
    415, 310, 311, 312, 13, 82, 81, 80, 191,
]

FACE_OVAL_IDX = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
    361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
    176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
    162, 21, 54, 103, 67, 109,
]

# Curated nose subset (bridge + tip + wings). See docstring note above.
NOSE_IDX = [
    1, 2, 98, 327, 168, 197, 5, 4, 45, 275, 440, 220,
]

JAW_BAND_WIDTH_FRACTION = 0.06  # ±6% of face width, per project spec


@dataclass
class FaceInfo:
    """Structured result of face detection + region extraction."""

    face_detected: bool
    image_width: int
    image_height: int
    bbox: Optional[tuple] = None  # (x_min, y_min, x_max, y_max) in pixels
    landmarks: Optional[np.ndarray] = None  # (478, 2) int32 pixel coords, or None
    confidence: Optional[float] = None  # mean landmark presence score, if available
    regions: Dict[str, np.ndarray] = field(default_factory=dict)  # name -> bool mask (H, W)
    region_polygons: Dict[str, np.ndarray] = field(default_factory=dict)  # name -> (N, 2) float pixel coords
    fallback_used: bool = False
    limitation: Optional[str] = None  # human-readable note when detection degrades


# ============================================================
# Landmarker (loaded once, reused)
# ============================================================

_landmarker: Optional[FaceLandmarker] = None


def _get_landmarker() -> FaceLandmarker:
    """Lazily create the FaceLandmarker (IMAGE mode), cached globally."""

    global _landmarker

    if _landmarker is not None:
        return _landmarker

    if not FACE_LANDMARKER_MODEL_PATH.exists() or FACE_LANDMARKER_MODEL_PATH.stat().st_size == 0:
        raise FileNotFoundError(
            f"Missing or empty MediaPipe model: {FACE_LANDMARKER_MODEL_PATH}. "
            "Download face_landmarker.task and place it there before calling detect_face()."
        )

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(FACE_LANDMARKER_MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )

    _landmarker = FaceLandmarker.create_from_options(options)
    return _landmarker


# ============================================================
# Helpers
# ============================================================

def _to_rgb_ndarray(image) -> np.ndarray:
    """Normalize a PIL image or ndarray to an RGB uint8 numpy array."""

    if isinstance(image, Image.Image):
        return np.array(image.convert("RGB"))

    if isinstance(image, np.ndarray):
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"Expected an (H, W, 3) RGB array, got shape {image.shape}")
        return np.ascontiguousarray(image.astype(np.uint8))

    raise TypeError(f"image must be a PIL.Image or RGB numpy array, got {type(image)}")


def _landmarks_to_pixels(face_landmarks, width: int, height: int) -> np.ndarray:
    """Convert normalized (0..1) landmarks to (N, 2) int32 pixel coordinates."""

    pts = np.array(
        [(lm.x * width, lm.y * height) for lm in face_landmarks],
        dtype=np.float32,
    )
    return pts


def _polygon_mask(polygon: np.ndarray, width: int, height: int) -> np.ndarray:
    """Rasterize a closed polygon (N, 2) float pixel coords into a boolean mask."""

    import cv2

    mask = np.zeros((height, width), dtype=np.uint8)
    pts = np.round(polygon).astype(np.int32)
    cv2.fillPoly(mask, [pts], color=1)
    return mask.astype(bool)


def _band_mask(polygon: np.ndarray, width: int, height: int, band_px: float) -> np.ndarray:
    """
    Build a ring/band mask straddling `polygon`'s boundary: dilate the filled
    polygon outward by `band_px` and erode it inward by `band_px`, then take
    the set difference (dilated - eroded). Used for jaw_boundary.
    """

    import cv2

    filled = _polygon_mask(polygon, width, height).astype(np.uint8)

    kernel_size = max(1, int(round(band_px)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * kernel_size + 1, 2 * kernel_size + 1))

    dilated = cv2.dilate(filled, kernel)
    eroded = cv2.erode(filled, kernel)

    band = (dilated.astype(bool)) & (~eroded.astype(bool))
    return band


def _build_regions(landmarks_px: np.ndarray, width: int, height: int) -> tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Build boolean region masks and their source polygons from pixel-space landmarks.

    Regions: face, left_eye, right_eye, mouth, nose, jaw_boundary, skin, background.
    """

    polygons: Dict[str, np.ndarray] = {
        "face": landmarks_px[FACE_OVAL_IDX],
        "left_eye": landmarks_px[LEFT_EYE_IDX],
        "right_eye": landmarks_px[RIGHT_EYE_IDX],
        "mouth": landmarks_px[LIPS_IDX],
        "nose": landmarks_px[NOSE_IDX],
    }

    face_mask = _polygon_mask(polygons["face"], width, height)
    left_eye_mask = _polygon_mask(polygons["left_eye"], width, height)
    right_eye_mask = _polygon_mask(polygons["right_eye"], width, height)
    mouth_mask = _polygon_mask(polygons["mouth"], width, height)
    nose_mask = _polygon_mask(polygons["nose"], width, height)

    face_width_px = float(landmarks_px[:, 0].max() - landmarks_px[:, 0].min())
    band_px = max(1.0, JAW_BAND_WIDTH_FRACTION * face_width_px)
    jaw_boundary_mask = _band_mask(polygons["face"], width, height, band_px)

    features_mask = left_eye_mask | right_eye_mask | mouth_mask | nose_mask
    skin_mask = face_mask & (~features_mask)

    background_mask = ~face_mask

    regions = {
        "face": face_mask,
        "left_eye": left_eye_mask,
        "right_eye": right_eye_mask,
        "mouth": mouth_mask,
        "nose": nose_mask,
        "jaw_boundary": jaw_boundary_mask,
        "skin": skin_mask,
        "background": background_mask,
    }

    return regions, polygons


def _fallback_face(width: int, height: int) -> FaceInfo:
    """
    Fallback when MediaPipe finds no face: try OpenCV Haar cascade if a
    cascade file is actually present in this OpenCV install (it is not,
    in the currently installed opencv-python build — this environment
    has no haarcascade XML files bundled). If unavailable, fall back to
    a proportional centered-face heuristic so the pipeline never crashes.
    """

    import cv2

    cascade_path = getattr(cv2.data, "haarcascades", "") + "haarcascade_frontalface_default.xml"

    if os.path.exists(cascade_path):
        # Haar path left in place for environments where the cascade IS present.
        # (Not exercised in this project's current OpenCV build.)
        return FaceInfo(
            face_detected=False,
            image_width=width,
            image_height=height,
            fallback_used=True,
            limitation="No face found by MediaPipe; Haar cascade fallback available but not implemented here.",
        )

    # Proportional heuristic fallback: assume a centered face occupying
    # roughly the middle 60% width / 70% height of the frame. This is a
    # coarse box only, with no landmarks and no fine-grained regions.
    box_w = int(width * 0.6)
    box_h = int(height * 0.7)
    x_min = (width - box_w) // 2
    y_min = int(height * 0.1)
    x_max = x_min + box_w
    y_max = y_min + box_h

    fallback_mask = np.zeros((height, width), dtype=bool)
    fallback_mask[y_min:y_max, x_min:x_max] = True

    return FaceInfo(
        face_detected=False,
        image_width=width,
        image_height=height,
        bbox=(x_min, y_min, x_max, y_max),
        regions={"face": fallback_mask, "background": ~fallback_mask},
        fallback_used=True,
        limitation=(
            "No face found by MediaPipe and no Haar cascade available in this "
            "OpenCV install; used a proportional centered-box fallback with no "
            "landmarks and no fine-grained regions."
        ),
    )


# ============================================================
# Public API
# ============================================================

def detect_face(image) -> FaceInfo:
    """
    Detect a face and extract landmarks + region masks.

    Args:
        image: PIL.Image (any mode) or RGB numpy array (H, W, 3), uint8.

    Returns:
        FaceInfo. If no face is found, `face_detected` is False and a
        best-effort fallback box/limitation note is included; this
        function never raises for "no face found".
    """

    rgb = _to_rgb_ndarray(image)
    height, width = rgb.shape[:2]

    landmarker = _get_landmarker()
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    result = landmarker.detect(mp_image)

    if not result.face_landmarks:
        return _fallback_face(width, height)

    face_landmarks = result.face_landmarks[0]

    if len(face_landmarks) != NUM_LANDMARKS:
        # Still usable, but flag the mismatch rather than silently assuming 478.
        limitation = f"Expected {NUM_LANDMARKS} landmarks, got {len(face_landmarks)}."
    else:
        limitation = None

    landmarks_px = _landmarks_to_pixels(face_landmarks, width, height)

    x_min = float(landmarks_px[:, 0].min())
    y_min = float(landmarks_px[:, 1].min())
    x_max = float(landmarks_px[:, 0].max())
    y_max = float(landmarks_px[:, 1].max())
    bbox = (int(x_min), int(y_min), int(x_max), int(y_max))

    presences = [lm.presence for lm in face_landmarks if lm.presence is not None]
    confidence = float(np.mean(presences)) if presences else None

    try:
        regions, polygons = _build_regions(landmarks_px, width, height)
    except Exception as exc:  # region extraction must never crash the whole call
        return FaceInfo(
            face_detected=True,
            image_width=width,
            image_height=height,
            bbox=bbox,
            landmarks=landmarks_px.astype(np.int32),
            confidence=confidence,
            fallback_used=True,
            limitation=f"Landmarks found but region-mask construction failed: {exc}",
        )

    return FaceInfo(
        face_detected=True,
        image_width=width,
        image_height=height,
        bbox=bbox,
        landmarks=landmarks_px.astype(np.int32),
        confidence=confidence,
        regions=regions,
        region_polygons=polygons,
        fallback_used=False,
        limitation=limitation,
    )
