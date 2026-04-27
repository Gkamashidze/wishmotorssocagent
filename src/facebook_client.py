from __future__ import annotations
import logging
import time
import uuid
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


def _build_multipart_utf8(
    fields: dict[str, str],
    file_name: str,
    file_data: bytes,
    file_mime: str,
) -> tuple[bytes, str]:
    """Build multipart/form-data with explicit UTF-8 charset on every text field.

    Standard requests/urllib3 send text fields without a Content-Type header,
    so Facebook defaults to latin-1 and emoji bytes get mangled. Building the
    body manually lets us declare charset=utf-8 explicitly on each text part.
    """
    boundary = "WishMotorsBoundary" + uuid.uuid4().hex
    sep = ("--" + boundary + "\r\n").encode("ascii")
    end = ("--" + boundary + "--\r\n").encode("ascii")
    parts: list[bytes] = []

    for name, value in fields.items():
        header = (
            f'Content-Disposition: form-data; name="{name}"\r\n'
            f'Content-Type: text/plain; charset=utf-8\r\n'
            f'\r\n'
        ).encode("ascii")
        parts.append(sep + header + value.encode("utf-8") + b"\r\n")

    file_header = (
        f'Content-Disposition: form-data; name="source"; filename="{file_name}"\r\n'
        f'Content-Type: {file_mime}\r\n'
        f'\r\n'
    ).encode("ascii")
    parts.append(sep + file_header + file_data + b"\r\n")
    parts.append(end)

    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def _publish_photo_with_message(
    page_id: str, access_token: str, message: str, image_path: str
) -> str:
    """Publish photo + message to Facebook page. Returns post_id.

    Sends message as a text/plain; charset=utf-8 multipart part so Facebook
    receives the emoji bytes declared as UTF-8 rather than defaulting to latin-1.
    """
    url = f"{_GRAPH_BASE}/{page_id}/photos"

    def _call():
        logger.info(
            "Publishing photo post — message length=%d, first 80 chars: %r",
            len(message), message[:80],
        )
        with open(image_path, "rb") as f:
            image_data = f.read()

        body, ct = _build_multipart_utf8(
            fields={"access_token": access_token, "message": message},
            file_name="photo.jpg",
            file_data=image_data,
            file_mime="image/jpeg",
        )

        response = requests.post(
            url,
            data=body,
            headers={"Content-Type": ct},
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

    POST to /photos with manually built multipart body where the message field
    carries Content-Type: text/plain; charset=utf-8 (explicit, not inferred).

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
