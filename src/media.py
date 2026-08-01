"""Public URL helpers for generated Instagram media."""


def public_image_url(base_url: str, approval_token: str) -> str:
    """Return a crawler-friendly URL with an explicit JPEG filename suffix."""
    return f"{base_url.rstrip('/')}/media/{approval_token}.jpg"
