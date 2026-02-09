"""Instagram Graph API publisher for posting approved content."""

import time

import httpx

from .config import get_settings

GRAPH_API_BASE = "https://graph.instagram.com/v24.0"


class InstagramPublishError(Exception):
    """Raised when Instagram publishing fails."""
    pass


def publish_post(caption: str, hashtags: str, image_url: str | None = None) -> str:
    """
    Publish a post to Instagram via Graph API.
    
    For now, this supports text posts with images (Instagram requires an image).
    The image_url must be a publicly accessible URL.
    
    Args:
        caption: The post caption text
        hashtags: Hashtags to append to caption
        image_url: Public URL of the image to post
    
    Returns:
        The Instagram post ID
        
    Raises:
        InstagramPublishError: If publishing fails
    """
    settings = get_settings()

    if not settings.instagram_access_token or not settings.instagram_account_id:
        raise InstagramPublishError(
            "Instagram credentials not configured. "
            "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID in .env"
        )

    if not image_url:
        raise InstagramPublishError(
            "Instagram requires an image for each post. "
            "Please provide a public image URL."
        )

    full_caption = f"{caption}\n\n{hashtags}"
    account_id = settings.instagram_account_id
    token = settings.instagram_access_token

    # Step 1: Create a media container
    container_url = f"{GRAPH_API_BASE}/{account_id}/media"
    container_payload = {
        "image_url": image_url,
        "caption": full_caption,
        "access_token": token,
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(container_url, data=container_payload)
        resp.raise_for_status()
        container_data = resp.json()

        if "id" not in container_data:
            raise InstagramPublishError(
                f"Failed to create media container: {container_data}"
            )

        container_id = container_data["id"]
        print(f"📦 Media container created: {container_id}")

        # Step 2: Wait for container to be ready (Instagram processes the image)
        _wait_for_container(client, container_id, token)

        # Step 3: Publish the container
        publish_url = f"{GRAPH_API_BASE}/{account_id}/media_publish"
        publish_payload = {
            "creation_id": container_id,
            "access_token": token,
        }

        resp = client.post(publish_url, data=publish_payload)
        resp.raise_for_status()
        publish_data = resp.json()

        if "id" not in publish_data:
            raise InstagramPublishError(
                f"Failed to publish post: {publish_data}"
            )

        post_id = publish_data["id"]
        print(f"✅ Published to Instagram! Post ID: {post_id}")
        return post_id


def _wait_for_container(
    client: httpx.Client, container_id: str, token: str, max_attempts: int = 10
):
    """Wait for Instagram to finish processing the media container."""
    for attempt in range(max_attempts):
        resp = client.get(
            f"{GRAPH_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        )
        data = resp.json()
        status = data.get("status_code")

        if status == "FINISHED":
            return
        elif status == "ERROR":
            raise InstagramPublishError(
                f"Media container failed: {data}"
            )

        print(f"⏳ Waiting for media processing... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(3)

    raise InstagramPublishError("Media processing timed out")


def validate_credentials() -> bool:
    """Check if Instagram credentials are valid."""
    settings = get_settings()

    if not settings.instagram_access_token or not settings.instagram_account_id:
        return False

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{GRAPH_API_BASE}/{settings.instagram_account_id}",
                params={
                    "fields": "id,username",
                    "access_token": settings.instagram_access_token,
                },
            )
            data = resp.json()
            if "username" in data:
                print(f"✅ Instagram connected: @{data['username']}")
                return True
            else:
                print(f"❌ Instagram validation failed: {data}")
                return False
    except Exception as e:
        print(f"❌ Instagram validation error: {e}")
        return False
