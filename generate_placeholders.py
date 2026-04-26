from __future__ import annotations

import hashlib
import argparse
import string
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

# Stable marker GUID appended to generated filenames so downstream code can
# identify these placeholders as profile-photo assets.
FILE_MARKER_GUID = "fb6c917a-4235-4fb1-a406-1db84c6ca8dd"

# Fluent UI PersonaInitialsColor palette (excluding transparent/black/gray).
PALETTE = [
    "#4F6BED",  # light blue
    "#0078D4",  # blue
    "#004E8C",  # dark blue
    "#038387",  # teal
    "#498205",  # green
    "#0B6A0B",  # dark green
    "#C239B3",  # light pink
    "#E3008C",  # pink
    "#881798",  # magenta
    "#5C2E91",  # purple
    "#CA5010",  # orange
    "#EE1111",  # red
    "#D13438",  # light red
    "#A4262C",  # dark red
    "#8764B8",  # violet
    "#986F0B",  # gold
    "#750B1C",  # burgundy
    "#7A7574",  # warm gray
    "#005B70",  # cyan
    "#8E562E",  # rust
    "#69797E",  # cool gray
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Teams-style initials placeholder images for all Latin "
            "first-name + last-name initial combinations (AA-ZZ)."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory where PNG files will be written (default: output)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=256,
        help="Image width/height in pixels (default: 256)",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=102,
        help="Font size in pixels (default: 102)",
    )
    parser.add_argument(
        "--font-path",
        type=Path,
        default=None,
        help="Optional path to a .ttf/.ttc font file",
    )
    parser.add_argument(
        "--circle-padding",
        type=int,
        default=0,
        help="Inner padding before drawing the circle (default: 0)",
    )
    return parser.parse_args()


# Base Latin letters plus common French accented letters.
INITIALS_ALPHABET = string.ascii_uppercase + "ÀÂÆÇÈÉÊËÎÏÔŒÙÛÜŸ"


def all_initial_pairs() -> Iterable[str]:
    for first in INITIALS_ALPHABET:
        for last in INITIALS_ALPHABET:
            yield f"{first}{last}"


def pick_color(initials: str) -> str:
    # MD5 hash gives a deterministic, uniformly distributed mapping to palette entries.
    digest = hashlib.md5(initials.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "little") % len(PALETTE)
    return PALETTE[index]


def load_font(font_path: Path | None, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path is not None:
        return ImageFont.truetype(str(font_path), font_size)

    candidate_fonts = [
        "segoeui.ttf",    # Segoe UI Regular (Windows)
        "segoeuisl.ttf",  # Segoe UI Semilight (Windows)
        "arial.ttf",      # Arial Regular fallback
        "DejaVuSans.ttf",
    ]
    for font_name in candidate_fonts:
        try:
            return ImageFont.truetype(font_name, font_size)
        except OSError:
            continue

    return ImageFont.load_default()


# Super-sample factor – draw at this multiple then downscale for smooth edges.
_SS = 4


def draw_placeholder(
    initials: str,
    size: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    circle_padding: int,
) -> Image.Image:
    ss = _SS
    hi = size * ss  # high-resolution canvas size

    image = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    color = pick_color(initials)
    pad = circle_padding * ss
    draw.ellipse((pad, pad, hi - pad - 1, hi - pad - 1), fill=color)

    text_bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    text_x = (hi - text_width) / 2 - text_bbox[0]
    text_y = (hi - text_height) / 2 - text_bbox[1]
    draw.text((text_x, text_y), initials, fill="white", font=font)

    image = image.resize((size, size), Image.LANCZOS)
    return image


def main() -> None:
    args = parse_args()

    if args.size < 32:
        raise ValueError("--size must be at least 32")
    if args.font_size < 8:
        raise ValueError("--font-size must be at least 8")
    if args.circle_padding < 0 or args.circle_padding * 2 >= args.size:
        raise ValueError("--circle-padding must be >= 0 and less than half of --size")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    font = load_font(args.font_path, args.font_size * _SS)

    count = 0
    for initials in all_initial_pairs():
        image = draw_placeholder(
            initials=initials,
            size=args.size,
            font=font,
            circle_padding=args.circle_padding,
        )
        output_file = args.output_dir / f"{initials}_{FILE_MARKER_GUID}.png"
        image.save(output_file, format="PNG")
        count += 1

    print(f"Generated {count} images in '{args.output_dir}' using marker GUID {FILE_MARKER_GUID}.")


if __name__ == "__main__":
    main()
