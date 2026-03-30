from __future__ import annotations
import logging
import os
import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_FONT_GEO_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/"
    "hinted/ttf/NotoSansGeorgian/NotoSansGeorgian-Bold.ttf"
)
_FONT_LAT_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/"
    "hinted/ttf/NotoSans/NotoSans-Regular.ttf"
)
_FONT_GEO_PATH = "/tmp/NotoSansGeorgian-Bold.ttf"
_FONT_LAT_PATH = "/tmp/NotoSans-Regular.ttf"


def _ensure_fonts() -> tuple[str, str]:
    for url, path in [(_FONT_GEO_URL, _FONT_GEO_PATH), (_FONT_LAT_URL, _FONT_LAT_PATH)]:
        if not os.path.exists(path):
            logger.info("Downloading font: %s", path)
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            logger.info("Font downloaded: %s", path)
    return _FONT_GEO_PATH, _FONT_LAT_PATH


def add_overlay(image_path: str, part_en: str, part_ka: str) -> str:
    """Add WISH MOTORS branding + Georgian/English part labels to image.
    Returns path to the new overlaid image."""
    font_geo, font_lat = _ensure_fonts()
    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    draw = ImageDraw.Draw(img, "RGBA")

    # — Bottom banner: semi-transparent dark navy strip —
    banner_h = int(height * 0.22)
    banner_top = height - banner_h
    draw.rectangle(
        [(0, banner_top), (width, height)],
        fill=(27, 43, 92, 220),
    )

    # — Cyan accent line above banner —
    accent_h = max(4, int(height * 0.005))
    draw.rectangle(
        [(0, banner_top), (width, banner_top + accent_h)],
        fill=(0, 180, 216, 255),
    )

    fnt_brand = ImageFont.truetype(font_lat, size=int(height * 0.040))

    # — Georgian part name: auto-size to fit banner width —
    max_text_width = int(width * 0.90)
    font_size = int(height * 0.075)
    while font_size > int(height * 0.030):
        fnt_ka = ImageFont.truetype(font_geo, size=font_size)
        bbox = draw.textbbox((0, 0), part_ka, font=fnt_ka)
        if (bbox[2] - bbox[0]) <= max_text_width:
            break
        font_size -= 2

    ka_y = banner_top + int(banner_h * 0.15)
    bbox = draw.textbbox((0, 0), part_ka, font=fnt_ka)
    ka_x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((ka_x + 2, ka_y + 2), part_ka, font=fnt_ka, fill=(0, 0, 0, 130))
    draw.text((ka_x, ka_y), part_ka, font=fnt_ka, fill=(255, 255, 255, 255))

    # — WISH MOTORS brand (bottom right) —
    brand = "WISH MOTORS"
    bbox = draw.textbbox((0, 0), brand, font=fnt_brand)
    bw = bbox[2] - bbox[0]
    brand_x = width - bw - int(width * 0.04)
    brand_y = height - int(banner_h * 0.35)
    draw.text((brand_x, brand_y), brand, font=fnt_brand, fill=(0, 180, 216, 255))

    out_path = image_path.replace(".jpg", "_final.jpg")
    img.save(out_path, "JPEG", quality=95)
    logger.info("Overlay applied: %s", out_path)
    return out_path
