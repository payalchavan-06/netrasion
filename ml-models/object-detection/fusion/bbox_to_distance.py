#!/usr/bin/env python3
"""
================================================================================
bbox_to_distance.py — Bounding Box + MiDaS Depth Fusion
Blind Assist Navigator | Person 4 (Computer Vision)
================================================================================

DELIVERABLE: /ml-models/object-detection/fusion/bbox_to_distance.py

INPUTS:
    - YOLOv8-nano detections: list of dicts with keys [label, confidence, bbox]
    - MiDaS depth map: H×W numpy array (float32, relative inverse depth)
    - Camera intrinsics (optional): for metric calibration

OUTPUT:
    - CV Detection Array (API Contract Section B):
      [
        {
          "label": str,
          "confidence": float,
          "bbox": [x1, y1, x2, y2],      // pixel coordinates, original image space
          "distance_m": float,           // APPROXIMATE metric distance (>=1m trusted)
          "direction": "left" | "center" | "right"
        }
      ]

FUSION LOGIC:
    1. DIRECTION: Determined by bbox center x vs image center.
       Thresholds tuned for 640×640 input (Person 2's CameraX pipeline).

    2. DISTANCE: MiDaS outputs relative inverse depth. We convert to approximate
       meters using a lightweight median-depth + calibration model.

       CRITICAL: Person 6 (Brain) overrides CV distance with ultrasonic data
       when distance < 1m (Problem Statement Section 6.5). Therefore, our 
       distance_m must be MOST ACCURATE in the 1m–4m range (mid-field navigation).

    3. PERFORMANCE: Entire fusion must complete in < 20ms on a mid-range CPU
       (leaving headroom for YOLO inference to stay under 200ms total).

HANDOFF:
    - Consumed by: Person 6 (Brain Layer) via sensor-fusion engine
    - Schema enforced: docs/api-interfaces.md Section B (source of truth)

WHAT NOT TO TOUCH:
    - No ultrasonic logic (Person 1 + Person 6)
    - No LLM / priority queue logic (Person 6)
    - No INT8 quantization (third member)
    - No Android CameraX code (Person 2)
================================================================================
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import time


# ==============================================================================
# 1. CONFIGURATION & CALIBRATION
# ==============================================================================

class FusionConfig:
    """Tunable parameters for the fusion pipeline."""

    # Image dimensions — MUST match YOLO input size (640×640 per spec)
    IMG_WIDTH: int = 640
    IMG_HEIGHT: int = 640

    # Direction thresholds (fraction of image width from left edge)
    # Tuned for wearable camera FOV (~60–70° horizontal)
    DIR_LEFT_THRESHOLD: float = 0.35      # bbox center < 35% → left
    DIR_RIGHT_THRESHOLD: float = 0.65     # bbox center > 65% → right
    # 35%–65% → center

    # Depth sampling — we shrink bbox by this margin to avoid edge artifacts
    # (MiDaS can bleed depth at object boundaries)
    DEPTH_MARGIN_PX: int = 8

    # MiDaS depth → meters calibration.
    # MiDaS outputs relative inverse depth d_rel ≈ α / depth_m.
    # We estimate α via simple calibration: depth_m = SCALE_FACTOR / (d_rel + EPS)
    # 
    # DEFAULT: Approximate for a typical smartphone camera (focal length ~500px,
    # sensor height ~3mm). This is OVERRIDDEN by per-device calibration below.
    DEPTH_SCALE_FACTOR: float = 80.0      # meters * depth_unit
    DEPTH_EPS: float = 1e-3               # prevent division by zero

    # Distance clamping — CV is trusted 1m–4m; outside this, flag uncertainty
    MIN_CV_DISTANCE_M: float = 0.5        # below this, ultrasonic takes over anyway
    MAX_CV_DISTANCE_M: float = 8.0        # beyond this, depth is unreliable

    # Performance guard: if > this many detections, process top-N by confidence
    MAX_DETECTIONS_PER_FRAME: int = 10


# ==============================================================================
# 2. CALIBRATION HELPER
# ==============================================================================

def calibrate_depth_scale(
    depth_map: np.ndarray,
    known_distance_m: float,
    bbox: Tuple[int, int, int, int]
) -> float:
    """
    Compute DEPTH_SCALE_FACTOR for a specific camera device.

    Call this once during setup with a known-distance object (e.g., person 
    standing exactly 2.0m from camera). Store the returned factor in 
    FusionConfig.DEPTH_SCALE_FACTOR for that device.

    Args:
        depth_map: MiDaS output for the calibration frame
        known_distance_m: Ground-truth distance to object in meters
        bbox: (x1, y1, x2, y2) bounding box of the calibration object

    Returns:
        scale_factor: float — store this and reuse for all future frames
    """
    x1, y1, x2, y2 = bbox
    # Add margin
    m = FusionConfig.DEPTH_MARGIN_PX
    x1, y1 = max(0, x1 + m), max(0, y1 + m)
    x2, y2 = min(depth_map.shape[1], x2 - m), min(depth_map.shape[0], y2 - m)

    if x2 <= x1 or y2 <= y1:
        raise ValueError("Calibration bbox too small after margin.")

    roi = depth_map[y1:y2, x1:x2]
    median_depth = float(np.median(roi))

    # depth_m = scale / (median_depth + eps)  →  scale = depth_m * (median_depth + eps)
    scale_factor = known_distance_m * (median_depth + FusionConfig.DEPTH_EPS)

    print(f"[CALIBRATION] median_depth={median_depth:.4f}, known_dist={known_distance_m}m")
    print(f"[CALIBRATION] Computed scale_factor={scale_factor:.2f}")
    print(f"[CALIBRATION] → Set FusionConfig.DEPTH_SCALE_FACTOR = {scale_factor:.2f}")

    return scale_factor


# ==============================================================================
# 3. CORE FUSION FUNCTIONS
# ==============================================================================

def compute_direction(bbox: List[int], img_width: int = 640) -> str:
    """
    Map bbox center-x to spatial direction.

    Returns:
        "left" | "center" | "right"
    """
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2.0
    norm_cx = center_x / img_width

    if norm_cx < FusionConfig.DIR_LEFT_THRESHOLD:
        return "left"
    elif norm_cx > FusionConfig.DIR_RIGHT_THRESHOLD:
        return "right"
    else:
        return "center"


def compute_distance_from_depth(
    depth_map: np.ndarray,
    bbox: List[int],
    scale_factor: Optional[float] = None
) -> float:
    """
    Convert MiDaS relative depth within a bbox to approximate meters.

    Strategy:
        1. Extract depth ROI from bbox (with margin to avoid edge bleed)
        2. Use MEDIAN depth (robust to outliers / partial occlusion)
        3. Convert via inverse relation: distance ≈ scale / (depth + eps)
        4. Clamp to valid CV range

    Args:
        depth_map: H×W float32 array from MiDaS-small
        bbox: [x1, y1, x2, y2] in pixel coordinates (same space as depth_map)
        scale_factor: Override config scale (useful if per-device calibrated)

    Returns:
        distance_m: float — approximate metric distance
    """
    if scale_factor is None:
        scale_factor = FusionConfig.DEPTH_SCALE_FACTOR

    x1, y1, x2, y2 = bbox
    h, w = depth_map.shape

    # Clamp to image bounds
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))

    # Shrink ROI by margin to avoid boundary artifacts
    m = FusionConfig.DEPTH_MARGIN_PX
    x1, y1 = min(x2 - 1, x1 + m), min(y2 - 1, y1 + m)
    x2, y2 = max(x1 + 1, x2 - m), max(y1 + 1, y2 - m)

    if x2 <= x1 or y2 <= y1:
        # Fallback: bbox too small, use single center pixel
        cx, cy = int((bbox[0] + bbox[2]) // 2), int((bbox[1] + bbox[3]) // 2)
        cx, cy = max(0, min(w-1, cx)), max(0, min(h-1, cy))
        median_depth = float(depth_map[cy, cx])
    else:
        roi = depth_map[y1:y2, x1:x2]
        median_depth = float(np.median(roi))

    # Inverse depth → meters
    distance_m = scale_factor / (median_depth + FusionConfig.DEPTH_EPS)

    # Clamp to sensible CV range
    distance_m = max(FusionConfig.MIN_CV_DISTANCE_M, 
                     min(FusionConfig.MAX_CV_DISTANCE_M, distance_m))

    return round(distance_m, 2)


def fuse_detections(
    yolo_detections: List[Dict],
    depth_map: np.ndarray,
    img_width: int = 640,
    img_height: int = 640,
    depth_scale_factor: Optional[float] = None
) -> List[Dict]:
    """
    Fuse YOLO bounding boxes with MiDaS depth map into CV Detection Array.

    This is the PRIMARY function consumed by Person 6 (Brain Layer).

    Args:
        yolo_detections: List of dicts from YOLO inference, each containing:
            {
                "label": str,           # e.g., "person"
                "confidence": float,    # e.g., 0.87
                "bbox": [x1, y1, x2, y2]  # pixel coords, 640×640 space
            }
        depth_map: H×W numpy array from MiDaS-small (256×256 or 640×640)
        img_width: Width of original image (default 640)
        img_height: Height of original image (default 640)
        depth_scale_factor: Per-device calibration factor (optional)

    Returns:
        CV Detection Array matching API Contract Section B:
        [
            {
                "label": str,
                "confidence": float,
                "bbox": [x1, y1, x2, y2],
                "distance_m": float,
                "direction": "left" | "center" | "right"
            }
        ]
    """
    t0 = time.perf_counter()

    # Guard: limit number of detections to process (performance)
    if len(yolo_detections) > FusionConfig.MAX_DETECTIONS_PER_FRAME:
        # Sort by confidence descending, keep top-N
        yolo_detections = sorted(
            yolo_detections, 
            key=lambda d: d.get("confidence", 0), 
            reverse=True
        )[:FusionConfig.MAX_DETECTIONS_PER_FRAME]

    # Ensure depth map is float32 and correct shape
    if depth_map.dtype != np.float32:
        depth_map = depth_map.astype(np.float32)

    # If depth map is 256×256 (MiDaS-small native output) but bbox is 640×640,
    # we need to scale bboxes to depth space OR upscale depth to image space.
    # Upscaling depth is cheaper (one resize) than scaling every bbox.
    dh, dw = depth_map.shape
    if dh != img_height or dw != img_width:
        import cv2
        depth_map = cv2.resize(depth_map, (img_width, img_height), 
                               interpolation=cv2.INTER_LINEAR)

    output = []
    for det in yolo_detections:
        bbox = det["bbox"]

        # Compute direction (fast: O(1))
        direction = compute_direction(bbox, img_width)

        # Compute distance from depth (fast: median over small ROI)
        distance_m = compute_distance_from_depth(
            depth_map, bbox, scale_factor=depth_scale_factor
        )

        fused = {
            "label": str(det["label"]),
            "confidence": float(det["confidence"]),
            "bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
            "distance_m": distance_m,
            "direction": direction
        }
        output.append(fused)

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Performance assertion — must stay well under budget
    if elapsed_ms > 20:
        print(f"[WARN] Fusion latency {elapsed_ms:.1f}ms exceeds 20ms target.")

    return output


# ==============================================================================
# 4. CONVENIENCE WRAPPER (Person 6 calls this)
# ==============================================================================

def run_fusion(
    yolo_results,
    depth_map: np.ndarray,
    confidence_threshold: float = 0.3,
    depth_scale_factor: Optional[float] = None
) -> List[Dict]:
    """
    High-level wrapper that accepts raw Ultralytics YOLO results object.

    Args:
        yolo_results: Ultralytics Results object (from model.predict())
        depth_map: MiDaS depth output
        confidence_threshold: Minimum confidence to include detection
        depth_scale_factor: Per-device calibration

    Returns:
        CV Detection Array (API Contract Section B)
    """
    detections = []

    for box in yolo_results[0].boxes:
        conf = float(box.conf[0])
        if conf < confidence_threshold:
            continue

        xyxy = box.xyxy[0].cpu().numpy().astype(int)
        label = yolo_results[0].names[int(box.cls[0])]

        detections.append({
            "label": label,
            "confidence": conf,
            "bbox": xyxy.tolist()
        })

    return fuse_detections(
        detections, 
        depth_map, 
        depth_scale_factor=depth_scale_factor
    )


# ==============================================================================
# 5. SELF-TEST / SANITY CHECK
# ==============================================================================

if __name__ == "__main__":
    print("="*80)
    print("bbox_to_distance.py — Self-Test")
    print("="*80)

    # Simulate inputs
    np.random.seed(42)
    fake_depth = np.random.uniform(10, 50, (640, 640)).astype(np.float32)

    fake_detections = [
        {"label": "person", "confidence": 0.91, "bbox": [120, 200, 280, 500]},
        {"label": "bicycle", "confidence": 0.78, "bbox": [400, 250, 580, 480]},
        {"label": "pole", "confidence": 0.65, "bbox": [300, 100, 340, 400]},
    ]

    # Artificially set depth values so we get known-ish distances
    # person at ~2.5m → depth value ≈ 80/2.5 = 32
    fake_depth[200:500, 120:280] = 32.0
    # bicycle at ~1.8m → depth value ≈ 80/1.8 = 44.4
    fake_depth[250:480, 400:580] = 44.4
    # pole at ~3.0m → depth value ≈ 80/3.0 = 26.7
    fake_depth[100:400, 300:340] = 26.7

    result = fuse_detections(fake_detections, fake_depth)

    print("\nFused CV Detection Array:")
    for det in result:
        print(f"  {det['label']:10s} | conf={det['confidence']:.2f} | "
              f"dist={det['distance_m']:.1f}m | dir={det['direction']:6s} | "
              f"bbox={det['bbox']}")

    # Verify schema compliance
    required_keys = {"label", "confidence", "bbox", "distance_m", "direction"}
    for det in result:
        assert set(det.keys()) == required_keys, f"Schema mismatch: {det.keys()}"
        assert det["direction"] in {"left", "center", "right"}
        assert len(det["bbox"]) == 4

    print("\n[OK] All schema checks passed.")
    print("[OK] Output matches docs/api-interfaces.md Section B.")
    print("="*80)
