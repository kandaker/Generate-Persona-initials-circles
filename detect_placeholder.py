"""Detect whether a profile picture is a generated initials placeholder.

This module implements structural detection that works even after JPEG
re-encoding.  It checks:

1. Corners are dark (background outside the circle).
2. A sampling ring at ~65% radius is a single solid color from our palette.
3. Color uniformity in that ring is high (low std-dev per channel).
4. White pixels are present in the center (text).

Usage:
    python detect_placeholder.py photo1.jpg photo2.png ...
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import NamedTuple

from PIL import Image
import numpy as np

# The same palette from generate_placeholders.py.
PALETTE = [
    (0x4F, 0x6B, 0xED),
    (0x00, 0x78, 0xD4),
    (0x00, 0x4E, 0x8C),
    (0x03, 0x83, 0x87),
    (0x49, 0x82, 0x05),
    (0x0B, 0x6A, 0x0B),
    (0xC2, 0x39, 0xB3),
    (0xE3, 0x00, 0x8C),
    (0x88, 0x17, 0x98),
    (0x5C, 0x2E, 0x91),
    (0xCA, 0x50, 0x10),
    (0xEE, 0x11, 0x11),
    (0xD1, 0x34, 0x38),
    (0xA4, 0x26, 0x2C),
    (0x87, 0x64, 0xB8),
    (0x98, 0x6F, 0x0B),
    (0x75, 0x0B, 0x1C),
    (0x7A, 0x75, 0x74),
    (0x00, 0x5B, 0x70),
    (0x8E, 0x56, 0x2E),
    (0x69, 0x79, 0x7E),
]

# Detection thresholds.
CORNER_BRIGHTNESS_MAX = 40        # corners must be darker than this
COLOR_DISTANCE_MAX = 25.0         # max Euclidean distance to a palette color
RING_STD_DEV_MAX = 15.0           # max per-channel std-dev in the ring
WHITE_PIXEL_MIN_RATIO = 0.02     # minimum fraction of center pixels that are white
WHITE_BRIGHTNESS_MIN = 220        # R, G, B all above this = "white"


class DetectionResult(NamedTuple):
    is_placeholder: bool
    confidence: float  # 0.0 – 1.0
    matched_color: tuple[int, int, int] | None
    details: dict


def _sample_ring(pixels: np.ndarray, cx: float, cy: float, radius: float, n: int = 64) -> np.ndarray:
    """Sample n points around a ring at the given radius."""
    samples = []
    for i in range(n):
        angle = 2 * math.pi * i / n
        x = int(cx + radius * math.cos(angle))
        y = int(cy + radius * math.sin(angle))
        h, w = pixels.shape[:2]
        x = max(0, min(w - 1, x))
        y = max(0, min(h - 1, y))
        samples.append(pixels[y, x])
    return np.array(samples)


def _color_distance(c1: np.ndarray, c2: tuple[int, int, int]) -> float:
    return float(np.sqrt(np.sum((c1.astype(float) - np.array(c2, dtype=float)) ** 2)))


def _closest_palette_color(avg_color: np.ndarray) -> tuple[float, tuple[int, int, int]]:
    best_dist = float("inf")
    best_color = PALETTE[0]
    for color in PALETTE:
        dist = _color_distance(avg_color, color)
        if dist < best_dist:
            best_dist = dist
            best_color = color
    return best_dist, best_color


def detect(image_path: str | Path) -> DetectionResult:
    """Analyze an image and determine if it's a generated initials placeholder."""
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img)
    h, w = pixels.shape[:2]
    cx, cy = w / 2, h / 2
    radius = min(w, h) / 2

    details: dict = {}
    score = 0.0

    # --- Check 1: Corners should be dark ---
    corner_size = max(1, int(min(w, h) * 0.08))
    corners = [
        pixels[0:corner_size, 0:corner_size],
        pixels[0:corner_size, w - corner_size:w],
        pixels[h - corner_size:h, 0:corner_size],
        pixels[h - corner_size:h, w - corner_size:w],
    ]
    corner_brightness = float(np.mean([np.mean(c) for c in corners]))
    details["corner_brightness"] = round(corner_brightness, 1)
    if corner_brightness < CORNER_BRIGHTNESS_MAX:
        score += 0.25
    else:
        details["corner_fail"] = f"brightness {corner_brightness:.0f} > {CORNER_BRIGHTNESS_MAX}"

    # --- Check 2: Ring at 80% radius matches a palette color ---
    # Use 80% to avoid white text bleeding into the ring for wide chars (M, W, Œ).
    ring_samples = _sample_ring(pixels, cx, cy, radius * 0.80, n=64)
    avg_color = np.mean(ring_samples, axis=0)
    dist, matched = _closest_palette_color(avg_color)
    details["ring_avg_color"] = [int(x) for x in avg_color]
    details["closest_palette_color"] = list(matched)
    details["color_distance"] = round(dist, 1)
    if dist < COLOR_DISTANCE_MAX:
        score += 0.30
    else:
        details["color_fail"] = f"distance {dist:.1f} > {COLOR_DISTANCE_MAX}"

    # --- Check 3: Ring uniformity (low std-dev) ---
    ring_std = float(np.mean(np.std(ring_samples, axis=0)))
    details["ring_std_dev"] = round(ring_std, 1)
    if ring_std < RING_STD_DEV_MAX:
        score += 0.25
    else:
        details["uniformity_fail"] = f"std {ring_std:.1f} > {RING_STD_DEV_MAX}"

    # --- Check 4: White pixels in center ---
    center_r = int(radius * 0.25)
    y_start = max(0, int(cy - center_r))
    y_end = min(h, int(cy + center_r))
    x_start = max(0, int(cx - center_r))
    x_end = min(w, int(cx + center_r))
    center_region = pixels[y_start:y_end, x_start:x_end]
    white_mask = np.all(center_region > WHITE_BRIGHTNESS_MIN, axis=2)
    white_ratio = float(np.mean(white_mask))
    details["white_ratio_center"] = round(white_ratio, 3)
    if white_ratio >= WHITE_PIXEL_MIN_RATIO:
        score += 0.20
    else:
        details["white_fail"] = f"ratio {white_ratio:.3f} < {WHITE_PIXEL_MIN_RATIO}"

    is_placeholder = score >= 0.75
    return DetectionResult(
        is_placeholder=is_placeholder,
        confidence=round(score, 2),
        matched_color=matched if dist < COLOR_DISTANCE_MAX else None,
        details=details,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect generated initials placeholders.")
    parser.add_argument("images", nargs="+", type=Path, help="Image files to check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed results")
    args = parser.parse_args()

    for path in args.images:
        if not path.exists():
            print(f"  {path}: FILE NOT FOUND")
            continue
        result = detect(path)
        status = "PLACEHOLDER" if result.is_placeholder else "NOT placeholder"
        print(f"  {path.name}: {status} (confidence: {result.confidence:.0%})")
        if args.verbose:
            for k, v in result.details.items():
                print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
