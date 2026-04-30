from __future__ import annotations
import logging
import time
import requests

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v21.0"
_MAX_ATTEMPTS = 3


def _retry(func, *args, **kwargs):
    """Run func with exponential backoff. Raises on final failure."""
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            wait = 2 ** attempt * 3  # 3s, 6s
            logger.warning(
                "Facebook attempt %d/%d failed: %s. Retrying in %ds...",
                attempt + 1, _MAX_ATTEMPTS, exc, wait,
            )
            time.sleep(wait)


def _publish_photo_with_message(
    page_id: str, access_token: str, message: str, image_path: str
) -> str:
    """Publish photo + message to Facebook page. Returns post_id.

    Sends message and access_token as URL query parameters (percent-encoded UTF-8)
    so Facebook decodes them unambiguously regardless of multipart charset handling.
    Only the image is sent in the multipart body.
    """
    url = f"{_GRAPH_BASE}/{page_id}/photos"

    def _call():
        logger.info(
            "Publishing photo post — message length=%d, first 80 chars: %r",
            len(message), message[:80],
        )
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = requests.post(
            url,
            params={"access_token": access_token, "message": message},
            files={"source": ("photo.jpg", image_data, "image/jpeg")},
            timeout=60,
        )
        if not response.ok:
            fb_error = response.json().get("error", {})
            msg = fb_error.get("message", response.text[:300])
            code = fb_error.get("code", response.status_code)
            logger.error(
                "Photo publish error %s: %s | full_response=%s",
                code, msg, response.text[:500],
            )
            raise requests.HTTPError(f"Facebook error {code}: {msg}", response=response)
        data = response.json()
        post_id = data.get("post_id") or data.get("id", "unknown")
        logger.info("Photo post published → post_id=%s", post_id)
        return post_id

    return _retry(_call)


def delete_facebook_post(post_id: str, access_token: str) -> bool:
    """Delete a Facebook post by ID. Returns True if deleted successfully."""
    try:
        response = requests.delete(
            f"{_GRAPH_BASE}/{post_id}",
            params={"access_token": access_token},
            timeout=30,
        )
        if response.ok:
            logger.info("Deleted Facebook post: %s", post_id)
            return True
        fb_error = response.json().get("error", {})
        msg = fb_error.get("message", response.text[:200])
        code = fb_error.get("code", response.status_code)
        raise requests.HTTPError(f"Facebook error {code}: {msg}", response=response)
    except requests.HTTPError:
        raise
    except Exception as exc:
        logger.error("Delete request failed: %s", exc)
        raise


def verify_post(post_id: str, access_token: str) -> str | None:
    """Fetch permalink URL for a published post. Returns URL or None on failure."""
    try:
        response = requests.get(
            f"{_GRAPH_BASE}/{post_id}",
            params={"access_token": access_token, "fields": "permalink_url"},
            timeout=15,
        )
        if response.ok:
            return response.json().get("permalink_url")
    except Exception as exc:
        logger.warning("Could not fetch post URL for %s: %s", post_id, exc)
    return None


def publish_to_facebook(
    page_id: str,
    page_access_token: str,
    message: str,
    image_path: str,
) -> dict[str, str]:
    """Publish photo + message to Facebook page.

    POST to /photos with message as a URL query parameter (percent-encoded UTF-8)
    and source image as multipart file.

    Returns dict with keys: page_post_id, page_url.
    """
    page_post_id = _publish_photo_with_message(
        page_id, page_access_token, message, image_path
    )
    page_url = verify_post(page_post_id, page_access_token)

    return {
        "page_post_id": page_post_id,
        "page_url": page_url or "",
    }
