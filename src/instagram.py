"""Instagram Graph API publisher for posting approved content."""

import asyncio

import httpx

from .config import get_settings

GRAPH_API_BASE = "https://graph.instagram.com/v24.0"


class InstagramPublishError(Exception):
    """Raised when Instagram publishing fails."""


async def publish_post(
    caption: str, hashtags: str, image_url: str | None = None
) -> str:
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

    print(
        f"🖼️ Feed image_url sent to Meta: {image_url} "
        f"(account={account_id}, token=…{token[-6:]})"
    )

    try:
        # Step 1: Create a media container
        container_url = f"{GRAPH_API_BASE}/{account_id}/media"
        container_payload = {
            "image_url": image_url,
            "caption": full_caption,
            "access_token": token,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(container_url, data=container_payload)
            _ensure_success(resp, "creating the Instagram media container")
            container_data = resp.json()

            if "id" not in container_data:
                raise InstagramPublishError("Instagram returned no media container ID")

            container_id = container_data["id"]
            print(f"📦 Media container created: {container_id}")

            # Step 2: Wait for container to be ready (Instagram processes the image)
            await _wait_for_container(client, container_id, token)

            # Step 3: Publish the container
            publish_url = f"{GRAPH_API_BASE}/{account_id}/media_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": token,
            }

            resp = await client.post(publish_url, data=publish_payload)
            _ensure_success(resp, "publishing the Instagram media container")
            publish_data = resp.json()

            if "id" not in publish_data:
                raise InstagramPublishError("Instagram returned no published post ID")

            post_id = publish_data["id"]
            print(f"✅ Published to Instagram! Post ID: {post_id}")
            return post_id
    except InstagramPublishError:
        raise
    except httpx.HTTPError as exc:
        raise InstagramPublishError("Instagram API request failed") from exc


async def publish_story(image_url: str) -> str:
    """
    Publish an image story via Graph API.

    Stories have no caption; image_url must be publicly fetchable by Meta.

    Returns:
        The Instagram story media ID

    Raises:
        InstagramPublishError: If publishing fails
    """
    settings = get_settings()

    if not settings.instagram_access_token or not settings.instagram_account_id:
        raise InstagramPublishError(
            "Instagram credentials not configured. "
            "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID in .env"
        )

    account_id = settings.instagram_account_id
    token = settings.instagram_access_token

    try:
        container_url = f"{GRAPH_API_BASE}/{account_id}/media"
        container_payload = {
            "media_type": "STORIES",
            "image_url": image_url,
            "access_token": token,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(container_url, data=container_payload)
            _ensure_success(resp, "creating the Instagram story container")
            container_data = resp.json()

            if "id" not in container_data:
                raise InstagramPublishError("Instagram returned no story container ID")

            container_id = container_data["id"]
            print(f"📦 Story container created: {container_id}")

            await _wait_for_container(client, container_id, token)

            publish_url = f"{GRAPH_API_BASE}/{account_id}/media_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": token,
            }

            resp = await client.post(publish_url, data=publish_payload)
            _ensure_success(resp, "publishing the Instagram story")
            publish_data = resp.json()

            if "id" not in publish_data:
                raise InstagramPublishError("Instagram returned no published story ID")

            story_id = publish_data["id"]
            print(f"✅ Story published! ID: {story_id}")
            return story_id
    except InstagramPublishError:
        raise
    except httpx.HTTPError as exc:
        raise InstagramPublishError("Instagram API request failed") from exc


async def _wait_for_container(
    client: httpx.AsyncClient,
    container_id: str,
    token: str,
    max_attempts: int = 10,
):
    """Wait for Instagram to finish processing the media container."""
    for attempt in range(max_attempts):
        resp = await client.get(
            f"{GRAPH_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        )
        _ensure_success(resp, "checking Instagram media processing")
        data = resp.json()
        status = data.get("status_code")

        if status == "FINISHED":
            return
        elif status == "ERROR":
            raise InstagramPublishError(f"Media container failed: {data}")

        print(f"⏳ Waiting for media processing... (attempt {attempt + 1}/{max_attempts})")
        await asyncio.sleep(3)

    raise InstagramPublishError("Media processing timed out")


def _ensure_success(response: httpx.Response, action: str):
    """Raise a safe error that never includes the access token or request URL."""
    if response.is_success:
        return
    try:
        error = response.json().get("error", {})
        error.pop("fbtrace_id", None)
        print(f"❌ Graph API error while {action}: {error}")
        message = error.get("message")
    except ValueError:
        message = None
    detail = message or f"HTTP {response.status_code}"
    raise InstagramPublishError(f"Instagram failed while {action}: {detail}")


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
    except (httpx.HTTPError, ValueError) as e:
        print(f"❌ Instagram validation error: {e}")
        return False
