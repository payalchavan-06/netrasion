#!/usr/bin/env python3
"""
================================================================================
YOLOv8-nano Training Pipeline — Week 1 Warm-Up
Blind Assist Navigator | Person 4 (Computer Vision)
================================================================================

DELIVERABLE: Proves the YOLOv8-nano training pipeline on GPU (Colab/RTX 3050).
             Outputs best.pt → handed to third member for INT8 quantization.

WEEK 1 GOAL: "Elephant detector warm-up on laptop (YOLO pipeline proven)"

USAGE:
    $ python train_yolo8n_warmup.py --data coco128.yaml --epochs 50 --imgsz 640

    For Payal's dataset (Week 2+):
    $ python train_yolo8n_warmup.py --data /ml-models/datasets/data.yaml --epochs 100

HARDWARE TARGET: Google Colab (T4) or local RTX 3050 (4GB VRAM).
                 YOLOv8-nano trains comfortably in < 2GB VRAM at batch=8.

SPEC COMPLIANCE:
    - Model: YOLOv8-nano (per Problem Statement Section 3, non-negotiable)
    - Input size: 640×640 (per spec, Person 2 tuned CameraX pipeline around this)
    - Output: best.pt (PyTorch weights, handed to quantization specialist)
================================================================================
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------------------------
# 1. ENVIRONMENT SETUP
# ------------------------------------------------------------------------------

def setup_environment():
    """Verify Ultralytics is available; provide install hint if not."""
    try:
        import ultralytics
        print(f"[OK] Ultralytics {ultralytics.__version__} detected.")
    except ImportError:
        print("[FAIL] Ultralytics not found. Install:  pip install ultralytics")
        sys.exit(1)

    # Verify CUDA if available (expected on Colab/RTX 3050)
    import torch
    if torch.cuda.is_available():
        print(f"[OK] CUDA available: {torch.cuda.get_device_name(0)}")
    else:
        print("[WARN] CUDA not available — training will be VERY slow on CPU.")
        print("       Expected on Colab or RTX 3050 machine.")

# ------------------------------------------------------------------------------
# 2. TRAINING CONFIGURATION
# ------------------------------------------------------------------------------

TRAIN_CONFIG = {
    # Model architecture — DO NOT CHANGE without team agreement (Person 2 dependency)
    "model": "yolov8n.pt",           # nano variant, COCO-pretrained backbone

    # Training hyperparameters tuned for 2GB VRAM (RTX 3050 / Colab T4)
    "epochs": 50,
    "batch": 8,                      # fits in ~1.8GB VRAM for 640×640
    "imgsz": 640,                    # NON-NEGOTIABLE (per Problem Statement)
    "workers": 4,                    # dataloader workers
    "patience": 15,                  # early stopping patience

    # Augmentation — conservative for navigation safety (don't overfit to artifacts)
    "hsv_h": 0.015,                  # hue jitter (low — traffic light colors matter)
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    "degrees": 5.0,                  # slight rotation (wearable camera tilt)
    "translate": 0.1,
    "scale": 0.5,
    "fliplr": 0.5,

    # Optimization
    "optimizer": "AdamW",
    "lr0": 0.001,
    "lrf": 0.01,                     # final lr = lr0 * lrf
    "weight_decay": 0.0005,

    # Logging
    "project": "runs/detect",
    "name": "blind_assist_nav",
    "exist_ok": True,
    "pretrained": True,
    "verbose": True,
}

# ------------------------------------------------------------------------------
# 3. WARM-UP DATASET (Week 1)
# ------------------------------------------------------------------------------
"""
WEEK 1 uses COCO128 as the warm-up dataset to prove the pipeline works end-to-end.
COCO128 contains 128 images with 80 COCO classes including 'elephant' (class 20).

WEEK 2 SWAP: Replace --data argument with Payal's annotated dataset:
    /ml-models/datasets/data.yaml

    Expected structure of Payal's dataset:
        datasets/
        ├── data.yaml
        ├── train/
        │   ├── images/
        │   └── labels/
        └── val/
            ├── images/
            └── labels/

    data.yaml format:
        path: /ml-models/datasets
        train: train/images
        val: val/images
        nc: 8
        names: ['person', 'bicycle', 'car', 'dog', 'stairs', 'pole', 'bench', 'drain']
"""

# ------------------------------------------------------------------------------
# 4. TRAINING EXECUTION
# ------------------------------------------------------------------------------

def run_training(data_yaml: str, epochs: int = None, imgsz: int = None, batch: int = None):
    """Execute YOLOv8-nano training with project-specified constraints."""

    from ultralytics import YOLO

    config = TRAIN_CONFIG.copy()
    config["data"] = data_yaml
    if epochs is not None:
        config["epochs"] = epochs
    if imgsz is not None:
        config["imgsz"] = imgsz
    if batch is not None:
        config["batch"] = batch

    print("\n" + "="*80)
    print("BLIND ASSIST NAVIGATOR — YOLOv8-nano Training Pipeline")
    print("Week 1 Warm-Up | Person 4 (Computer Vision)")
    print("="*80)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Dataset:    {data_yaml}")
    print(f"Model:      {config['model']}")
    print(f"Image size: {config['imgsz']}×{config['imgsz']} (FIXED)")
    print(f"Epochs:     {config['epochs']}")
    print(f"Batch:      {config['batch']}")
    print("="*80 + "\n")

    # Load pretrained nano model
    model = YOLO(config.pop("model"))

    # Train
    results = model.train(**config)

    # --------------------------------------------------------------------------
    # POST-TRAINING: Export best.pt to expected location
    # --------------------------------------------------------------------------

    best_pt_src = Path(results.best)
    output_dir = Path("/ml-models/object-detection/weights")
    output_dir.mkdir(parents=True, exist_ok=True)
    best_pt_dst = output_dir / "best.pt"

    # Copy best.pt to canonical location for handoff to quantization specialist
    import shutil
    shutil.copy2(best_pt_src, best_pt_dst)

    print("\n" + "="*80)
    print("TRAINING COMPLETE")
    print("="*80)
    print(f"Best weights (source):  {best_pt_src}")
    print(f"Best weights (canonical): {best_pt_dst}")
    print(f"mAP50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")
    print(f"mAP50:    {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    print("\n>>> Handoff: Give best.pt to third member for INT8 TFLite quantization.")
    print("="*80)

    return results

# ------------------------------------------------------------------------------
# 5. VALIDATION / BENCHMARKING
# ------------------------------------------------------------------------------

def benchmark_model(weights_path: str = "runs/detect/blind_assist_nav/weights/best.pt"):
    """Run validation and latency benchmark on the trained model."""
    from ultralytics import YOLO
    import time
    import numpy as np

    print("\n" + "="*80)
    print("LATENCY BENCHMARK")
    print("="*80)

    model = YOLO(weights_path)

    # Validate on dataset
    val_results = model.val()
    print(f"Validation mAP50-95: {val_results.box.map:.4f}")

    # Warm-up inference latency test (simulates phone-like load)
    dummy_input = np.random.randint(0, 255, (1, 3, 640, 640), dtype=np.uint8)

    # Warm-up runs
    for _ in range(10):
        model.predict(dummy_input, verbose=False)

    # Timed runs
    times = []
    for _ in range(50):
        t0 = time.perf_counter()
        model.predict(dummy_input, verbose=False)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)  # ms

    times = np.array(times)
    print(f"Inference latency (GPU, batch=1, 640×640):")
    print(f"  Mean:  {times.mean():.2f} ms")
    print(f"  P50:   {np.percentile(times, 50):.2f} ms")
    print(f"  P95:   {np.percentile(times, 95):.2f} ms")
    print(f"  P99:   {np.percentile(times, 99):.2f} ms")

    # Budget check: CV inference must be < 200ms end-to-end (includes fusion math)
    budget_headroom = 200 - times.mean()
    print(f"\nBudget: < 200ms/frame | Headroom for fusion math: {budget_headroom:.1f} ms")
    if budget_headroom < 20:
        print("[WARN] Tight headroom — fusion math must be < 20ms. Optimize bbox_to_distance.py")
    else:
        print("[OK] Comfortable headroom for fusion math.")

    print("="*80)

# ------------------------------------------------------------------------------
# 6. MAIN
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YOLOv8-nano Training Pipeline for Blind Assist Navigator"
    )
    parser.add_argument(
        "--data", 
        type=str, 
        default="coco128.yaml",
        help="Path to dataset YAML (default: coco128.yaml for warm-up)"
    )
    parser.add_argument("--epochs", type=int, default=None, help="Override epochs")
    parser.add_argument("--imgsz", type=int, default=None, help="Override image size (DON'T)")
    parser.add_argument("--batch", type=int, default=None, help="Override batch size")
    parser.add_argument("--benchmark", action="store_true", help="Run post-train benchmark")

    args = parser.parse_args()

    setup_environment()

    if args.imgsz is not None and args.imgsz != 640:
        print("[ERROR] imgsz must be 640×640 per project spec. Aborting.")
        sys.exit(1)

    results = run_training(args.data, args.epochs, args.imgsz, args.batch)

    if args.benchmark:
        benchmark_model()
