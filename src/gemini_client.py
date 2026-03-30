from __future__ import annotations
import base64
import logging
import tempfile
import requests

logger = logging.getLogger(__name__)

_TEXT_MODEL = "gemini-1.5-flash"
_TEXT_API = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/{model}:generateContent"
)
_IMAGE_API = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/imagen-3.0-generate-001:predict"
)


def generate_post_text(prompt: str, api_key: str) -> str:
    """Generate Georgian post text using Gemini v1 REST API."""
    url = _TEXT_API.format(model=_TEXT_MODEL)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(
            url,
            json=payload,
            params={"key": api_key},
            timeout=60,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        logger.info("Text generated successfully (%d chars)", len(text))
        return text
    except Exception as exc:
        logger.error("Gemini text generation failed: %s", exc)
        raise


def generate_post_image(prompt: str, api_key: str) -> str:
    """Generate 3D Pixar-style image using Imagen 3. Returns path to saved /tmp file."""
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
        return tmp.name
    except Exception as exc:
        logger.error("Imagen generation failed: %s", exc)
        raise
