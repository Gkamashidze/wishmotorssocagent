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


def _upload_photo_unpublished(
    page_id: str, access_token: str, image_path: str
) -> str:
    """Upload photo with published=false. Returns photo media_fbid (no page prefix).

    This is step 1 of two-step publish. We do not attach the message here —
    /photos message field truncates 4-byte UTF-8 (emoji) to '?'. The message
    is sent in step 2 via /feed which accepts full UTF-8.
    """
    url = f"{_GRAPH_BASE}/{page_id}/photos"

    def _call():
        with open(image_path, "rb") as image_file:
            response = requests.post(
                url,
                params={"access_token": access_token},
                data={"published": "false"},
                files={"source": ("photo.jpg", image_file, "image/jpeg")},
                timeout=60,
            )
        if not response.ok:
            fb_error = response.json().get("error", {})
            msg = fb_error.get("message", response.text[:300])
            code = fb_error.get("code", response.status_code)
            logger.error(
                "Photo upload error %s: %s | full_response=%s",
                code, msg, response.text[:500],
            )
            raise requests.HTTPError(f"Facebook error {code}: {msg}", response=response)
        photo_id = response.json().get("id", "unknown")
        logger.info("Photo uploaded unpublished → media_fbid=%s", photo_id)
        return photo_id

    return _retry(_call)


def _publish_feed_with_photo(
    page_id: str, access_token: str, message: str, photo_id: str
) -> str:
    """Step 2: create /feed post with message + attached photo. Returns post_id.

    Why JSON body with ensure_ascii=False + explicit charset=utf-8:
    - /photos message field silently strips 4-byte UTF-8 chars (emoji) to '?'.
      3-byte chars (Georgian, Cyrillic, etc.) survive — only emoji break.
    - /feed endpoint handles full UTF-8 correctly when the body is JSON.
    - requests.post(json=...) uses ensure_ascii=True by default which converts
      emoji to \\uXXXX escape pairs. We serialize manually with ensure_ascii=False
      so the body contains raw UTF-8 bytes — no escaping ambiguity for Facebook
      to mishandle.
    """
    url = f"{_GRAPH_BASE}/{page_id}/feed"

    def _call():
        logger.info(
            "Publishing feed post — message length=%d, first 80 chars: %r",
            len(message), message[:80],
        )
        body = json.dumps(
            {
                "message": message,
                "attached_media": [{"media_fbid": photo_id}],
            },
            ensure_ascii=False,
        ).encode("utf-8")

        response = requests.post(
            url,
            params={"access_token": access_token},
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=60,
        )
        if not response.ok:
            fb_error = response.json().get("error", {})
            msg = fb_error.get("message", response.text[:300])
            code = fb_error.get("code", response.status_code)
            logger.error(
                "Feed publish error %s: %s | photo_id=%s | full_response=%s",
                code, msg, photo_id, response.text[:500],
            )
            raise requests.HTTPError(f"Facebook error {code}: {msg}", response=response)
        data = response.json()
        post_id = data.get("id") or data.get("post_id", "unknown")
        logger.info("Feed post published → post_id=%s", post_id)
        return post_id

    return _retry(_call)


def _verify_emoji_preserved(post_id: str, access_token: str, sent_message: str) -> None:
    """Read back the stored message and log whether emoji survived. Diagnostic only —
    never raises. Compares supplementary-plane codepoints (emoji) sent vs stored."""
    try:
        response = requests.get(
            f"{_GRAPH_BASE}/{post_id}",
            params={"access_token": access_token, "fields": "message"},
            timeout=15,
        )
        if not response.ok:
            logger.warning("Verify read failed: %s", response.text[:200])
            return
        stored = response.json().get("message", "")
        sent_emoji = sum(1 for c in sent_message if ord(c) > 0xFFFF)
        stored_emoji = sum(1 for c in stored if ord(c) > 0xFFFF)
        stored_q = stored.count("?")
        ok = sent_emoji == stored_emoji
        logger.info(
            "Emoji verify: sent=%d stored=%d ?_count=%d %s",
            sent_emoji, stored_emoji, stored_q,
            "✓ PRESERVED" if ok else "✗ LOST",
        )
    except Exception as exc:
        logger.warning("Verify check failed (non-fatal): %s", exc)


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
    """Publish photo + message to Facebook page via two-step /photos → /feed flow.

    Step 1: upload photo unpublished → media_fbid
    Step 2: create /feed post with message + attached_media as JSON (UTF-8)
    Step 3: verify emoji were preserved server-side (diagnostic log only)

    Returns dict with keys: page_post_id, page_url.
    """
    photo_id = _upload_photo_unpublished(page_id, page_access_token, image_path)
    page_post_id = _publish_feed_with_photo(
        page_id, page_access_token, message, photo_id
    )
    _verify_emoji_preserved(page_post_id, page_access_token, message)
    page_url = verify_post(page_post_id, page_access_token)

    return {
        "page_post_id": page_post_id,
        "page_url": page_url or "",
    }
