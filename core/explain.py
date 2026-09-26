"""
core/explain.py

Model-agnostic occlusion-based explainability for the S1 ensemble
(Model A / ViT + Model B / SigLIP + Model C / EfficientNet).

This module does NOT assume ViT, SigLIP and EfficientNet expose comparable
internal layers for Grad-CAM. Instead it measures attribution purely by
observation: occlude part of the image, rerun the whole S1 ensemble, and
compare the resulting fake-probability score to the original.

    attribution = baseline_score - occluded_score

Positive attribution: occluding that region LOWERED the fake score, i.e.
that region was contributing evidence toward "fake" (rendered warm/red).
Negative attribution: occluding that region RAISED the fake score, i.e.
that region was pushing the prediction toward "real" (rendered cool/blue).

This module reports contribution to the model's score only. It never
claims a region "is fake" or "is manipulated", and it never fabricates
or manually assigns an attribution value — every number here comes from
an actual rerun of the S1 ensemble on an actually-occluded image.

Two complementary outputs:
    A. Region attribution, using core.face.FaceInfo regions (unchanged
       from the original explainability step).
    B. A spatial 7x7 occlusion heatmap over the face region (or the
       whole image if no face bbox is available), which is new/expanded
       in this revision: it now scopes to the face for resolution,
       batches occlusion inference for speed, and is saved both as an
       image (original | overlay side by side) and as raw JSON data.

Does NOT implement: ELA, FFT, noise analysis, metadata analysis, video,
fusion across signals, or a FastAPI endpoint. Those are separate steps.
Does NOT change Model A, Model B, Model C or the S1 ensemble weights.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import torch
from PIL import Image

from detector.s1_ensemble import predict_s1
from models import model_a as _model_a
from models import model_b as _model_b
from models import model_c as _model_c
from core.face import FaceInfo, detect_face

# ============================================================
# Config
# ============================================================

GRID_ROWS = 7
GRID_COLS = 7
BLUR_KERNEL_FRACTION = 0.5  # blur kernel size as a fraction of the region's bbox side
MIN_BLUR_KERNEL = 15        # never blur with a kernel smaller than this (must be odd)
BATCH_CHUNK_SIZE = 16       # cap per-forward-pass batch size (GPU memory safety)
FACE_REGION_PADDING = 0.25  # pad the face bbox by this fraction on each side for grid context

# Mirrors the weights in detector/s1_ensemble.py exactly. Duplicated here
# (not imported) only because the models do not expose a batched predict
# function and s1_ensemble.py's per-image implementation is intentionally
# left untouched; these three numbers must stay in sync with that file.
S1_WEIGHT_A = 0.3333
S1_WEIGHT_B = 0.3333
S1_WEIGHT_C = 0.3334

REGION_NAMES = [
    "face",
    "left_eye",
    "right_eye",
    "nose",
    "mouth",
    "jaw_boundary",
    "skin",
    "background",
]

REGION_LABELS = {
    "face": "Face",
    "left_eye": "Left eye",
    "right_eye": "Right eye",
    "nose": "Nose",
    "mouth": "Mouth",
    "jaw_boundary": "Jaw boundary",
    "skin": "Skin",
    "background": "Background",
}


@dataclass
class ExplainResult:
    """Result of S1 occlusion-based attribution for one image."""

    original_score: float
    regions: Dict[str, float] = field(default_factory=dict)          # region -> attribution
    regions_available: bool = False                                    # False if no regions at all
    top_regions: List[Tuple[str, float]] = field(default_factory=list)  # sorted by |attribution|, desc
    heatmap_path: Optional[str] = None
    heatmap_json_path: Optional[str] = None
    grid_scores: Optional[np.ndarray] = None       # raw (GRID_ROWS, GRID_COLS) attribution values
    grid_region_box: Optional[Tuple[int, int, int, int]] = None  # (x0,y0,x1,y1) the grid covers
    face_detected: bool = False
    n_images_scored: int = 0
    baseline_seconds: float = 0.0
    occlusion_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    limitation: Optional[str] = None


# ============================================================
# Batched S1 scoring
#
# detector/s1_ensemble.predict_s1() is left completely untouched and is
# used for the authoritative single-image baseline score. For the many
# occlusion evaluations (8 regions + 49 grid cells per image), scoring
# one image at a time is wasteful, so this batches the same three
# already-loaded models/processors directly. The per-model math and the
# ensemble weights below are identical to s1_ensemble.py -- this is a
# batched *re-execution* of that logic, not a change to it.
# ============================================================

def _predict_s1_batch_chunk(images_rgb: List[np.ndarray]) -> np.ndarray:
    pil_images = [Image.fromarray(im).convert("RGB") for im in images_rgb]

    # --- Model A (ViT): sigmoid of the single logit ---
    inputs_a = _model_a.processor(images=pil_images, return_tensors="pt")
    inputs_a = {k: v.to(_model_a.device) for k, v in inputs_a.items()}
    with torch.inference_mode():
        out_a = _model_a.model(**inputs_a)
    scores_a = torch.sigmoid(out_a.logits[:, 0]).detach().cpu().numpy()

    # --- Model B (SigLIP): softmax, class 0 = Fake ---
    inputs_b = _model_b.processor(images=pil_images, return_tensors="pt")
    inputs_b = {k: v.to(_model_b.device) for k, v in inputs_b.items()}
    with torch.inference_mode():
        out_b = _model_b.model(**inputs_b)
    scores_b = torch.softmax(out_b.logits, dim=1)[:, 0].detach().cpu().numpy()

    # --- Model C (EfficientNetV2-S): sigmoid of the single logit ---
    tensors_c = [_model_c.transform(image=np.array(im))["image"] for im in pil_images]
    batch_c = torch.stack(tensors_c).to(_model_c.device)
    with torch.inference_mode():
        out_c = _model_c.model(batch_c)
        scores_c = torch.sigmoid(out_c.squeeze(-1)).detach().cpu().numpy()

    return S1_WEIGHT_A * scores_a + S1_WEIGHT_B * scores_b + S1_WEIGHT_C * scores_c


def _predict_s1_batch(images_rgb: List[np.ndarray], chunk_size: int = BATCH_CHUNK_SIZE) -> np.ndarray:
    """Score many images through S1 in GPU batches, chunked for memory safety."""

    if not images_rgb:
        return np.array([], dtype=np.float32)

    chunks = []
    for i in range(0, len(images_rgb), chunk_size):
        chunks.append(_predict_s1_batch_chunk(images_rgb[i:i + chunk_size]))
    return np.concatenate(chunks)


# ============================================================
# Occlusion
# ============================================================

def _blur_occlude(image_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Replace the pixels under `mask` with a heavily blurred version of the
    same image. This is a "neutral" occlusion: it destroys local detail
    without introducing the sharp, unnatural edges a flat color block
    would, and it leaves the image dimensions unchanged. Only pixels
    inside `mask` are modified.
    """

    ys, xs = np.where(mask)
    if len(ys) == 0:
        return image_rgb.copy()

    box_h = int(ys.max() - ys.min() + 1)
    box_w = int(xs.max() - xs.min() + 1)
    side = max(box_h, box_w)

    kernel = max(MIN_BLUR_KERNEL, int(side * BLUR_KERNEL_FRACTION))
    if kernel % 2 == 0:
        kernel += 1

    blurred = cv2.GaussianBlur(image_rgb, (kernel, kernel), 0)

    out = image_rgb.copy()
    out[mask] = blurred[mask]
    return out


def _rect_mask(height: int, width: int, y0: int, y1: int, x0: int, x1: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


# ============================================================
# Region attribution (batched)
# ============================================================

def _region_attribution(
    image_rgb: np.ndarray,
    face: FaceInfo,
    baseline_score: float,
) -> Tuple[Dict[str, float], int]:
    """
    Occlude every available named region once each, score all of them in
    a single batched S1 call, and return original_score - occluded_score
    per region, plus how many images were scored.
    """

    names = [name for name in REGION_NAMES if name in face.regions and face.regions[name].any()]
    if not names:
        return {}, 0

    occluded_images = [_blur_occlude(image_rgb, face.regions[name]) for name in names]
    occluded_scores = _predict_s1_batch(occluded_images)

    attributions = {
        name: float(baseline_score - score)
        for name, score in zip(names, occluded_scores)
    }
    return attributions, len(names)


# ============================================================
# Spatial grid heatmap (batched, scoped to the face region when known)
# ============================================================

def _face_region_box(face: Optional[FaceInfo], width: int, height: int) -> Tuple[int, int, int, int]:
    """
    Pick the region the 7x7 grid should cover: the (padded) face bbox when
    one is available -- including the fallback proportional box from
    core.face when no landmarks were found -- otherwise the whole image.
    """

    if face is not None and face.bbox is not None:
        x0, y0, x1, y1 = face.bbox
        pad_x = int((x1 - x0) * FACE_REGION_PADDING)
        pad_y = int((y1 - y0) * FACE_REGION_PADDING)
        x0 = max(0, x0 - pad_x)
        y0 = max(0, y0 - pad_y)
        x1 = min(width, x1 + pad_x)
        y1 = min(height, y1 + pad_y)
        if x1 > x0 and y1 > y0:
            return (x0, y0, x1, y1)

    return (0, 0, width, height)


def _grid_heatmap(
    image_rgb: np.ndarray,
    region_box: Tuple[int, int, int, int],
    baseline_score: float,
    rows: int = GRID_ROWS,
    cols: int = GRID_COLS,
) -> Tuple[np.ndarray, int]:
    """
    rows x cols occlusion grid over `region_box` (a sub-rectangle of the
    image, or the whole image). Every cell is occluded and all rows*cols
    occluded images are scored in one batched S1 pass.

    Returns the raw (rows, cols) attribution matrix (not yet normalized
    or resized) and the number of images scored.
    """

    x0, y0, x1, y1 = region_box
    sub_h = y1 - y0
    sub_w = x1 - x0
    cell_h = sub_h / rows
    cell_w = sub_w / cols

    occluded_images = []
    for r in range(rows):
        cy0 = y0 + int(round(r * cell_h))
        cy1 = y0 + int(round((r + 1) * cell_h))
        for c in range(cols):
            cx0 = x0 + int(round(c * cell_w))
            cx1 = x0 + int(round((c + 1) * cell_w))

            mask = _rect_mask(image_rgb.shape[0], image_rgb.shape[1], cy0, cy1, cx0, cx1)
            occluded_images.append(_blur_occlude(image_rgb, mask))

    occluded_scores = _predict_s1_batch(occluded_images)
    grid = (baseline_score - occluded_scores).reshape(rows, cols).astype(np.float32)

    return grid, len(occluded_images)


def _diverging_colormap(values: np.ndarray) -> np.ndarray:
    """
    Map values in [-1, 1] to a BGR diverging color image: positive
    (contributed toward "fake") -> warm/red, negative (pushed toward
    "real") -> cool/blue, near zero -> white/neutral. Standard
    increase/decrease convention (as in SHAP-style plots), not an
    arbitrary color choice.
    """

    v = np.clip(values, -1.0, 1.0)

    pos = np.clip(v, 0, 1)
    neg = np.clip(-v, 0, 1)

    b = 255 - pos * 255
    g = 255 - (pos + neg) * 255
    r = 255 - neg * 255

    bgr = np.stack([b, g, r], axis=-1)
    return np.clip(bgr, 0, 255).astype(np.uint8)


def _render_side_by_side(
    image_rgb: np.ndarray,
    grid: np.ndarray,
    region_box: Tuple[int, int, int, int],
    out_path: Path,
    alpha: float = 0.55,
) -> None:
    """
    Build [original | original+heatmap overlay] side by side and save it.
    The heatmap aligns exactly with the original image's dimensions; the
    overlay is semi-transparent so the underlying photo stays visible.
    Cells outside `region_box` (when the grid was scoped to the face) are
    left neutral/uncolored, not fabricated.
    """

    height, width = image_rgb.shape[:2]
    x0, y0, x1, y1 = region_box

    # Scale by the 90th percentile of |attribution| rather than the single
    # max: occlusion attribution is often dominated by one outlier cell,
    # and dividing by that outlier alone would wash out every other cell
    # to near-white even when they carry real, comparatively smaller
    # signal. This only rescales contrast for display; the raw values in
    # `grid` (saved separately to JSON) are untouched.
    scale = float(np.percentile(np.abs(grid), 90))
    if scale <= 1e-8:
        scale = float(np.abs(grid).max())
    normalized_sub = grid / scale if scale > 1e-8 else grid

    full_map = np.zeros((height, width), dtype=np.float32)
    resized_sub = cv2.resize(normalized_sub, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
    full_map[y0:y1, x0:x1] = resized_sub

    blur_sigma = max(1.0, (x1 - x0) * 0.01)
    full_map = cv2.GaussianBlur(full_map, (0, 0), sigmaX=blur_sigma)

    color_map = _diverging_colormap(full_map)  # already BGR-ordered

    original_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    overlay_bgr = cv2.addWeighted(color_map, alpha, original_bgr, 1 - alpha, 0)

    divider = np.full((height, 4, 3), 40, dtype=np.uint8)
    panel = np.hstack([original_bgr, divider, overlay_bgr])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), panel)


def _save_heatmap_json(
    out_path: Path,
    image_name: str,
    baseline_score: float,
    grid: np.ndarray,
    top_regions: List[Tuple[str, float]],
    face_detected: bool,
) -> None:
    payload = {
        "image": image_name,
        "baseline_score": float(baseline_score),
        "grid_size": [int(grid.shape[0]), int(grid.shape[1])],
        "attributions": grid.tolist(),
        "top_regions": [
            {"region": name, "attribution": float(value)} for name, value in top_regions
        ],
        "face_detected": bool(face_detected),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


# ============================================================
# Public API
# ============================================================

def explain(
    image: Union[Image.Image, np.ndarray],
    face: Optional[FaceInfo],
    heatmap_path: Path,
    heatmap_json_path: Optional[Path] = None,
    image_name: str = "image",
) -> ExplainResult:
    """
    Run occlusion-based explainability for one image against the S1 ensemble.

    Args:
        image: PIL.Image or RGB numpy array (H, W, 3), uint8.
        face: FaceInfo from core.face.detect_face(image), or None. Region
              attribution runs on whatever named regions `face.regions`
              actually contains (this includes the proportional fallback
              box when no landmarks were found); if there are none at
              all, region attribution is skipped and clearly marked.
        heatmap_path: where to save the side-by-side visualization (.jpg).
        heatmap_json_path: where to save the raw grid + region JSON. If
              omitted, defaults to heatmap_path with a .json suffix.
        image_name: recorded in the JSON payload's "image" field.

    Returns:
        ExplainResult with the baseline S1 score, per-region attribution,
        the top contributing regions, the raw spatial grid, and the
        saved file paths.
    """

    start = time.perf_counter()

    if isinstance(image, Image.Image):
        image_rgb = np.array(image.convert("RGB"))
    elif isinstance(image, np.ndarray):
        image_rgb = np.ascontiguousarray(image.astype(np.uint8))
    else:
        raise TypeError(f"image must be a PIL.Image or RGB numpy array, got {type(image)}")

    height, width = image_rgb.shape[:2]

    # 1. Baseline S1 score -- calls the real, unmodified ensemble.
    t0 = time.perf_counter()
    baseline_score = predict_s1(Image.fromarray(image_rgb))["score"]
    baseline_seconds = time.perf_counter() - t0

    n_images_scored = 0

    # 2. Region attribution (whatever regions are actually available).
    t0 = time.perf_counter()
    regions: Dict[str, float] = {}
    limitation = None

    if face is not None and face.regions:
        regions, n_regions_scored = _region_attribution(image_rgb, face, baseline_score)
        n_images_scored += n_regions_scored
    else:
        limitation = "No face regions available; region attribution skipped (spatial heatmap only)."

    regions_available = bool(regions)
    top_regions = sorted(regions.items(), key=lambda kv: abs(kv[1]), reverse=True)

    # 3. Spatial grid heatmap, scoped to the face region when we have one.
    region_box = _face_region_box(face, width, height)
    grid, n_grid_scored = _grid_heatmap(image_rgb, region_box, baseline_score)
    n_images_scored += n_grid_scored
    occlusion_seconds = time.perf_counter() - t0

    _render_side_by_side(image_rgb, grid, region_box, heatmap_path)

    json_path = heatmap_json_path or heatmap_path.with_suffix(".json")
    _save_heatmap_json(
        json_path,
        image_name,
        baseline_score,
        grid,
        top_regions,
        face_detected=bool(face and face.face_detected),
    )

    elapsed = time.perf_counter() - start

    return ExplainResult(
        original_score=baseline_score,
        regions=regions,
        regions_available=regions_available,
        top_regions=top_regions,
        heatmap_path=str(heatmap_path),
        heatmap_json_path=str(json_path),
        grid_scores=grid,
        grid_region_box=region_box,
        face_detected=bool(face and face.face_detected),
        n_images_scored=n_images_scored,
        baseline_seconds=baseline_seconds,
        occlusion_seconds=occlusion_seconds,
        elapsed_seconds=elapsed,
        limitation=limitation,
    )


def get_explainability(
    image_path: Union[str, Path],
    output_dir: Union[str, Path],
) -> dict:
    """
    Convenience wrapper around detect_face() + explain() that returns a
    single JSON-friendly dict, structured for a future frontend/API to
    consume directly without knowing about FaceInfo/ExplainResult:

        {
            "baseline_score": float,
            "heatmap_image": str,      # path to the side-by-side .jpg
            "heatmap_data": {...},      # same payload written to the .json
            "region_attributions": {region: float, ...},
            "top_regions": [{"region": ..., "attribution": ...}, ...],
            "face_detected": bool,
        }
    """

    image_path = Path(image_path)
    output_dir = Path(output_dir)

    image = Image.open(image_path).convert("RGB")
    face = detect_face(image)

    stem = image_path.stem
    heatmap_path = output_dir / f"{stem}_heatmap.jpg"
    json_path = output_dir / f"{stem}_heatmap.json"

    result = explain(image, face, heatmap_path, json_path, image_name=image_path.name)

    with open(json_path, "r", encoding="utf-8") as f:
        heatmap_data = json.load(f)

    return {
        "baseline_score": result.original_score,
        "heatmap_image": result.heatmap_path,
        "heatmap_data": heatmap_data,
        "region_attributions": result.regions,
        "top_regions": [{"region": name, "attribution": value} for name, value in result.top_regions],
        "face_detected": result.face_detected,
    }
