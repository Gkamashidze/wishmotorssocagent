from __future__ import annotations
import json
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


def _upload_photo_unpublished(page_id: str, access_token: str, image_path: str) -> str:
    """Upload image without publishing. Returns photo node ID.

    Using published=false keeps the image separate from the post so the
    message can be sent in a plain form-encoded body (emoji-safe).
    """
    url = f"{_GRAPH_BASE}/{page_id}/photos"

    def _call():
        with open(image_path, "rb") as image_file:
            response = requests.post(
                url,
                data={"published": "false", "access_token": access_token},
                files={"source": ("photo.jpg", image_file, "image/jpeg")},
                timeout=60,
            )
        if not response.ok:
            fb_error = response.json().get("error", {})
            msg = fb_error.get("message", response.text[:200])
            code = fb_error.get("code", response.status_code)
            logger.error("Photo upload error %s: %s", code, msg)
            raise requests.HTTPError(f"Facebook error {code}: {msg}", response=response)
        photo_id = response.json().get("id", "unknown")
        logger.info("Photo uploaded (unpublished) → photo_id=%s", photo_id)
        return photo_id

    return _retry(_call)


def _publish_feed_with_photo(page_id: str, access_token: str, message: str, photo_id: str) -> str:
    """Create feed post: message + attached photo. Returns post_id.

    Sends message as application/x-www-form-urlencoded (no files=).
    requests.urlencode percent-encodes every character — emoji arrive intact.
    Previous attempts failed because they used JSON body or multipart,
    both of which have charset ambiguity for the message field.
    """
    url = f"{_GRAPH_BASE}/{page_id}/feed"

    def _call():
        logger.info(
            "Publishing feed post — message length=%d, first 80 chars: %r",
            len(message), message[:80],
        )
        # No files= → Content-Type: application/x-www-form-urlencoded
        # requests uses urllib.parse.urlencode which percent-encodes to UTF-8
        response = requests.post(
            url,
            data={
                "message": message,
                "attached_media[0]": json.dumps({"media_fbid": photo_id}),
                "access_token": access_token,
            },
            timeout=60,
        )
        if not response.ok:
            fb_error = response.json().get("error", {})
            msg = fb_error.get("message", response.text[:300])
            code = fb_error.get("code", response.status_code)
            logger.error(
                "Feed post error %s: %s | photo_id=%s | full_response=%s",
                code, msg, photo_id, response.text[:500],
            )
            raise requests.HTTPError(f"Facebook error {code}: {msg}", response=response)
        data = response.json()
        post_id = data.get("id") or data.get("post_id", "unknown")
        logger.info("Feed post published → post_id=%s", post_id)
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

    Two-step approach:
      1. Upload image as unpublished photo → get photo_id
      2. POST to /feed with form-encoded message + attached_media (emoji-safe)

    Returns dict with keys: page_post_id, page_url.
    """
    photo_id = _upload_photo_unpublished(page_id, page_access_token, image_path)
    page_post_id = _publish_feed_with_photo(page_id, page_access_token, message, photo_id)
    page_url = verify_post(page_post_id, page_access_token)

    return {
        "page_post_id": page_post_id,
        "page_url": page_url or "",
    }
