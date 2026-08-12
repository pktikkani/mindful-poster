"""Public URL helpers for generated Instagram media."""

import httpx

# Meta's media fetcher refuses to download from tunnel domains (Graph API
# error 9004 "Only photo or video can be accepted as media type").
META_BLOCKED_HOSTS = ("trycloudflare.com", "ngrok-free.app", "ngrok.io", "localhost", "127.0.0.1")

UGUU_API = "https://uguu.se/upload.php"


class MediaUploadError(RuntimeError):
    """Raised when re-hosting an image for Meta fails."""


def public_image_url(base_url: str, approval_token: str) -> str:
    """Return a crawler-friendly URL with an explicit JPEG filename suffix."""
    return f"{base_url.rstrip('/')}/media/{approval_token}.jpg"


def is_meta_blocked_host(base_url: str) -> bool:
    """True if Meta will refuse to fetch media from this base URL."""
    return any(host in base_url for host in META_BLOCKED_HOSTS)


async def upload_for_meta(image_data: bytes, mime_type: str = "image/jpeg") -> str:
    """Temporarily re-host image bytes for media without a database-backed URL."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                UGUU_API,
                files={"files[]": ("post.jpg", image_data, mime_type)},
            )
    except httpx.HTTPError as exc:
        raise MediaUploadError("Image re-hosting request failed") from exc

    try:
        payload = resp.json()
        url = payload["files"][0]["url"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise MediaUploadError(f"Image re-hosting failed: {resp.text[:200]}") from exc
    if (
        not resp.is_success
        or payload.get("success") is not True
        or not url.startswith("https://")
    ):
        raise MediaUploadError(f"Image re-hosting failed: {resp.text[:200]}")
    return url
