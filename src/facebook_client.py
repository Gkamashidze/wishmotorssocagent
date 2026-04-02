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
    """Upload photo with caption to a Facebook page. Returns post ID."""
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
        data = response.json()
        post_id = data.get("post_id") or data.get("id", "unknown")
        logger.info("Posted to %s → post_id=%s", target_id, post_id)
        return post_id

    return _retry(_call)


def _share_link_to_group(group_id: str, access_token: str, page_url: str) -> str:
    """Share a page post URL to a group as a rich link preview. Returns post ID."""
    url = f"{_GRAPH_BASE}/{group_id}/feed"

    def _call():
        response = requests.post(
            url,
            params={"access_token": access_token, "link": page_url},
            timeout=60,
        )
        if not response.ok:
            fb_error = response.json().get("error", {})
            msg = fb_error.get("message", response.text[:200])
            code = fb_error.get("code", response.status_code)
            logger.error("Facebook group share error %s: %s", code, msg)
            raise requests.HTTPError(
                f"Facebook error {code}: {msg}", response=response
            )
        post_id = response.json().get("id", "unknown")
        logger.info("Shared link to group %s → post_id=%s", group_id, post_id)
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
    group_id: str,
    page_access_token: str,
    user_access_token: str,
    message: str,
    image_path: str,
) -> dict[str, str]:
    """Publish photo to page, then share the page post link to the group.

    Page publish is mandatory — raises on failure.
    Group share failure is logged but does not raise (page post stays live).
    Returns dict with keys: page_post_id, group_post_id, page_url, group_error.
    """
    page_post_id = _post_photo(page_id, page_access_token, message, image_path)
    page_url = verify_post(page_post_id, page_access_token)

    group_error = ""
    group_post_id = "failed"

    if not page_url:
        group_error = "გვერდის ბმული ვერ მოიძებნა — ჯგუფში გაზიარება შეუძლებელია"
        logger.error("Cannot share to group: page_url is empty for post %s", page_post_id)
    else:
        try:
            group_post_id = _share_link_to_group(group_id, user_access_token, page_url)
        except Exception as exc:
            logger.error(
                "Group share failed after %d attempts (page post %s is live): %s",
                _MAX_ATTEMPTS, page_post_id, exc,
            )
            group_error = str(exc)[:300]

    return {
        "page_post_id": page_post_id,
        "group_post_id": group_post_id,
        "page_url": page_url or "",
        "group_error": group_error,
    }
