from __future__ import annotations
import base64
import logging
import os
import tempfile
import time
import requests
from google import genai

logger = logging.getLogger(__name__)

_TEXT_MODEL = "gemini-2.5-flash"
_TEXT_MODEL_FALLBACK = "gemini-2.0-flash"  # used automatically when 2.5-flash is overloaded
_IMAGE_API = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/imagen-4.0-generate-001:predict"
)
_MAX_ATTEMPTS = 3


class ServiceUnavailableError(Exception):
    """Raised when Gemini/Imagen returns 503 or UNAVAILABLE — needs a long retry."""


def _is_service_unavailable(exc: Exception) -> bool:
    msg = str(exc).upper()
    return "503" in msg or "UNAVAILABLE" in msg

# Module-level client cache — one client per API key, not re-created on every call
_client_cache: dict[str, genai.Client] = {}


def _get_client(api_key: str) -> genai.Client:
    if api_key not in _client_cache:
        _client_cache[api_key] = genai.Client(api_key=api_key)
    return _client_cache[api_key]


def _retry(func, *args, **kwargs):
    """Run func with exponential backoff. Raises on final failure.

    503/UNAVAILABLE errors are raised immediately as ServiceUnavailableError
    so the caller (bot.py) can handle them with longer waits and user notification.
    """
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if _is_service_unavailable(exc):
                raise ServiceUnavailableError(str(exc)) from exc
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            wait = 2 ** attempt * 3  # 3s, 6s
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %ds...",
                attempt + 1, _MAX_ATTEMPTS, exc, wait,
            )
            time.sleep(wait)


def generate_post_text(prompt: str, api_key: str) -> str:
    """Generate Georgian post text using Gemini SDK.

    Tries _TEXT_MODEL first; on 503/UNAVAILABLE falls back to _TEXT_MODEL_FALLBACK immediately.
    """
    client = _get_client(api_key)

    for model in (_TEXT_MODEL, _TEXT_MODEL_FALLBACK):
        def _call(m=model):
            response = client.models.generate_content(model=m, contents=prompt)
            logger.info("Text generated with %s (%d chars)", m, len(response.text))
            return response.text

        try:
            return _retry(_call)
        except ServiceUnavailableError as exc:
            if model == _TEXT_MODEL_FALLBACK:
                logger.error("Both text models unavailable: %s", exc)
                raise
            logger.warning("%s unavailable, switching to fallback %s", model, _TEXT_MODEL_FALLBACK)
        except Exception as exc:
            logger.error("Gemini text generation failed (%s): %s", model, exc)
            raise

    raise ServiceUnavailableError("All text models unavailable")


def generate_post_image(prompt: str, api_key: str, part_en: str = "", part_ka: str = "") -> str:
    """Generate 3D Pixar-style image using Imagen. Returns path to saved /tmp file."""
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "1:1",
            "safetyFilterLevel": "block_some",
            "personGeneration": "dont_allow",
        },
    }

    def _call():
        response = requests.post(
            _IMAGE_API,
            json=payload,
            params={"key": api_key},
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["predictions"][0]["bytesBase64Encoded"]

    try:
        image_b64 = _retry(_call)
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
