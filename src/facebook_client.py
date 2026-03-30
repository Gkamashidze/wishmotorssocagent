from __future__ import annotations
import logging
import requests

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v21.0"


def _post_photo(target_id: str, access_token: str, caption: str, image_path: str) -> str:
    """Upload photo with caption to a Facebook page or group. Returns post ID."""
    url = f"{_GRAPH_BASE}/{target_id}/photos"
    with open(image_path, "rb") as image_file:
        response = requests.post(
            url,
            data={"caption": caption, "access_token": access_token},
            files={"source": image_file},
            timeout=60,
        )
    response.raise_for_status()
    post_id = response.json().get("id", "unknown")
    logger.info("Posted to %s → post_id=%s", target_id, post_id)
    return post_id


def publish_to_facebook(
    page_id: str,
    group_id: str,
    access_token: str,
    message: str,
    image_path: str,
) -> tuple[str, str]:
    """Publish to Facebook page and group. Returns (page_post_id, group_post_id)."""
    page_post_id = _post_photo(page_id, access_token, message, image_path)
    group_post_id = _post_photo(group_id, access_token, message, image_path)
    return page_post_id, group_post_id
