from __future__ import annotations
import base64
import logging
import os
import tempfile
import requests
from google import genai

logger = logging.getLogger(__name__)

_TEXT_MODEL = "gemini-2.5-flash"
_IMAGE_API = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/imagen-4.0-generate-001:predict"
)


def generate_post_text(prompt: str, api_key: str) -> str:
    """Generate Georgian post text using Gemini SDK."""
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=_TEXT_MODEL,
            contents=prompt,
        )
        logger.info("Text generated successfully (%d chars)", len(response.text))
        return response.text
    except Exception as exc:
        logger.error("Gemini text generation failed: %s", exc)
        raise


def generate_post_image(prompt: str, api_key: str, part_en: str = "", part_ka: str = "") -> str:
    """Generate 3D Pixar-style image using Imagen. Returns path to saved /tmp file."""
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "1:1",
            "safetyFilterLevel": "block_some",
            "personGeneration": "allow_adult",
        },
    }
    try:
        response = requests.post(
            _IMAGE_API,
            json=payload,
            params={"key": api_key},
            timeout=90,
        )
        response.raise_for_status()
        image_b64 = response.json()["predictions"][0]["bytesBase64Encoded"]
        image_bytes = base64.b64decode(image_b64)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir="/tmp")
        tmp.write(image_bytes)
        tmp.close()

        logger.info("Image generated and saved: %s", tmp.name)

        if part_en and part_ka:
            from src.image_overlay import add_overlay
            final_path = add_overlay(tmp.name, part_en, part_ka)
            os.remove(tmp.name)
            return final_path

        return tmp.name
    except Exception as exc:
        logger.error("Imagen generation failed: %s", exc)
        raise
