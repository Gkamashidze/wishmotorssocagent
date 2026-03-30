from __future__ import annotations
import logging
import os
import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_FONT_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/"
    "hinted/ttf/NotoSansGeorgian/NotoSansGeorgian-Regular.ttf"
)
_FONT_PATH = "/tmp/NotoSansGeorgian-Regular.ttf"


def _ensure_font() -> str:
    if not os.path.exists(_FONT_PATH):
        logger.info("Downloading Georgian font...")
        r = requests.get(_FONT_URL, timeout=30)
        r.raise_for_status()
        with open(_FONT_PATH, "wb") as f:
            f.write(r.content)
        logger.info("Georgian font downloaded: %s", _FONT_PATH)
    return _FONT_PATH


def add_overlay(image_path: str, part_en: str, part_ka: str) -> str:
    """Add WISH MOTORS branding + Georgian/English part labels to image.
    Returns path to the new overlaid image."""
    font_path = _ensure_font()
    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    draw = ImageDraw.Draw(img, "RGBA")

    # — Bottom banner: semi-transparent dark navy strip —
    banner_h = int(height * 0.22)
    banner_top = height - banner_h
    draw.rectangle(
        [(0, banner_top), (width, height)],
        fill=(27, 43, 92, 210),  # navy #1B2B5C with alpha
    )

    # — Cyan accent line above banner —
    accent_h = max(4, int(height * 0.005))
    draw.rectangle(
        [(0, banner_top), (width, banner_top + accent_h)],
        fill=(0, 180, 216, 255),  # cyan #00B4D8
    )

    font_large = ImageFont.truetype(font_path, size=int(height * 0.065))
    font_medium = ImageFont.truetype(font_path, size=int(height * 0.048))
    font_brand = ImageFont.truetype(font_path, size=int(height * 0.042))

    # — Georgian part name (top line of banner) —
    ka_y = banner_top + int(banner_h * 0.08)
    bbox = draw.textbbox((0, 0), part_ka, font=font_large)
    ka_x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((ka_x + 2, ka_y + 2), part_ka, font=font_large, fill=(0, 0, 0, 120))
    draw.text((ka_x, ka_y), part_ka, font=font_large, fill=(255, 255, 255, 255))

    # — English part name (second line) —
    en_y = ka_y + int(banner_h * 0.35)
    bbox = draw.textbbox((0, 0), part_en, font=font_medium)
    en_x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((en_x, en_y), part_en, font=font_medium, fill=(0, 180, 216, 255))

    # — WISH MOTORS brand (bottom right) —
    brand = "WISH MOTORS"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    bw = bbox[2] - bbox[0]
    brand_x = width - bw - int(width * 0.04)
    brand_y = height - int(banner_h * 0.32)
    draw.text((brand_x, brand_y), brand, font=font_brand, fill=(0, 180, 216, 255))

    out_path = image_path.replace(".jpg", "_final.jpg")
    img.save(out_path, "JPEG", quality=95)
    logger.info("Overlay applied: %s", out_path)
    return out_path
