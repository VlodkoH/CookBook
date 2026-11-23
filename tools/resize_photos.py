#!/usr/bin/env python3
"""Resizes recipe photos to 1200x750 (16:10) JPEG without EXIF metadata.

Usage:
    python tools/resize_photos.py photos_original
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "images"
SIZE = (1200, 750)
QUALITY = 78
MAX_BYTES = 180 * 1024


def process(src: Path, dst: Path) -> int:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, SIZE, Image.LANCZOS, centering=(0.5, 0.5))
        # Pillow does not copy EXIF unless passed explicitly, so metadata is dropped.
        im.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return dst.stat().st_size


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    src_dir = Path(sys.argv[1])
    files = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    if not files:
        print(f"No images found in {src_dir}")
        return 1

    OUT_DIR.mkdir(exist_ok=True)
    for src in files:
        dst = OUT_DIR / f"{src.stem.lower()}.jpg"
        size = process(src, dst)
        status = "OK" if size <= MAX_BYTES else "TOO BIG, lower QUALITY"
        print(f"{dst.name}: {size / 1024:.0f} KB  {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())