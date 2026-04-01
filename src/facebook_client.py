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


def _post_photo(target_id: str, access_token: str, caption: str, image_path: str) -> str:
    """Upload photo with caption to a Facebook page or group. Returns post ID."""
    url = f"{_GRAPH_BASE}/{target_id}/photos"

    def _call():
        with open(image_path, "rb") as image_file:
            response = requests.post(
                url,
                params={"access_token": access_token, "caption": caption},
                files={"source": image_file},
                timeout=60,
            )
        if not response.ok:
            fb_error = response.json().get("error", {})
            msg = fb_error.get("message", response.text[:200])
            code = fb_error.get("code", response.status_code)
            logger.error("Facebook API error %s for %s: %s", code, target_id, msg)
            raise requests.HTTPError(
                f"Facebook error {code}: {msg}", response=response
            )
        post_id = response.json().get("id", "unknown")
        logger.info("Posted to %s → post_id=%s", target_id, post_id)
        return post_id

    return _retry(_call)


def verify_post(post_id: str, access_token: str) -> str | None:
    """Fetch permalink URL for a published post. Returns URL or None on failure."""
    try:
        response = requests.get(
            f"{_GRAPH_BASE}/{post_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "permalink_url"},
            timeout=15,
        )
        if response.ok:
            return response.json().get("permalink_url")
    except Exception as exc:
        logger.warning("Could not fetch post URL for %s: %s", post_id, exc)
    return None


def publish_to_facebook(
    page_id: str,
    group_id: str,
    page_access_token: str,
    user_access_token: str,
    message: str,
    image_path: str,
) -> dict[str, str]:
    """Publish to Facebook page (page token) and group (user token).

    Page publish is mandatory — raises on failure.
    Group publish failure is logged but does not raise (page post stays live).
    Returns dict with keys: page_post_id, group_post_id, page_url, group_error.
    """
    page_post_id = _post_photo(page_id, page_access_token, message, image_path)
    page_url = verify_post(page_post_id, page_access_token)

    group_error = ""
    try:
        group_post_id = _post_photo(group_id, user_access_token, message, image_path)
    except Exception as exc:
        logger.error(
            "Group publish failed after %d attempts (page post %s is live): %s",
            _MAX_ATTEMPTS, page_post_id, exc,
        )
        group_post_id = "failed"
        group_error = str(exc)[:300]

    return {
        "page_post_id": page_post_id,
        "group_post_id": group_post_id,
        "page_url": page_url or "",
        "group_error": group_error,
    }
