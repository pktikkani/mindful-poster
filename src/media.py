"""Public URL helpers for generated Instagram media."""

import httpx

# Meta's media fetcher refuses to download from tunnel domains (Graph API
# error 9004 "Only photo or video can be accepted as media type").
META_BLOCKED_HOSTS = ("trycloudflare.com", "ngrok-free.app", "ngrok.io", "localhost", "127.0.0.1")

CATBOX_API = "https://catbox.moe/user/api.php"


class MediaUploadError(RuntimeError):
    """Raised when re-hosting an image for Meta fails."""


def public_image_url(base_url: str, approval_token: str) -> str:
    """Return a crawler-friendly URL with an explicit JPEG filename suffix."""
    return f"{base_url.rstrip('/')}/media/{approval_token}.jpg"


def is_meta_blocked_host(base_url: str) -> bool:
    """True if Meta will refuse to fetch media from this base URL."""
    return any(host in base_url for host in META_BLOCKED_HOSTS)


def upload_for_meta(image_data: bytes, mime_type: str = "image/jpeg") -> str:
    """Re-host the exact image bytes on a public host Meta will fetch from."""
    try:
        resp = httpx.post(
            CATBOX_API,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": ("post.jpg", image_data, mime_type)},
            timeout=60,
        )
    except httpx.HTTPError as exc:
        raise MediaUploadError("Image re-hosting request failed") from exc
    url = resp.text.strip()
    if not resp.is_success or not url.startswith("https://"):
        raise MediaUploadError(f"Image re-hosting failed: {url[:200]}")
    return url
