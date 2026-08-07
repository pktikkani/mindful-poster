"""LinkedIn Posts API publisher for posting approved content to the company page."""

import httpx

from .config import get_settings

API_BASE = "https://api.linkedin.com/rest"
LINKEDIN_VERSION = "202506"


class LinkedInPublishError(Exception):
    """Raised when LinkedIn publishing fails."""


def publish_post(
    caption: str, hashtags: str, image_data: bytes, mime_type: str = "image/jpeg"
) -> str:
    """
    Publish an image post to the LinkedIn company page.

    Unlike Instagram, LinkedIn accepts the image as a direct binary upload,
    so no publicly reachable image URL is required.

    Args:
        caption: The post caption text
        hashtags: Hashtags to append to caption
        image_data: Raw bytes of the image to post
        mime_type: MIME type of the image

    Returns:
        The LinkedIn post URN (e.g. urn:li:share:123)

    Raises:
        LinkedInPublishError: If publishing fails
    """
    settings = get_settings()

    if not settings.linkedin_access_token or not settings.linkedin_organization_id:
        raise LinkedInPublishError(
            "LinkedIn credentials not configured. "
            "Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORGANIZATION_ID in .env"
        )

    org_urn = f"urn:li:organization:{settings.linkedin_organization_id}"
    commentary = _escape_commentary(f"{caption}\n\n{hashtags}".strip())

    try:
        with httpx.Client(timeout=60) as client:
            # Step 1: Register the upload and get a one-time upload URL
            resp = client.post(
                f"{API_BASE}/images?action=initializeUpload",
                json={"initializeUploadRequest": {"owner": org_urn}},
                headers=_headers(settings.linkedin_access_token),
            )
            _ensure_success(resp, "initializing the LinkedIn image upload")
            value = resp.json().get("value", {})
            upload_url = value.get("uploadUrl")
            image_urn = value.get("image")
            if not upload_url or not image_urn:
                raise LinkedInPublishError("LinkedIn returned no upload URL or image URN")

            # Step 2: Upload the image bytes
            resp = client.put(
                upload_url,
                content=image_data,
                headers={
                    "Authorization": f"Bearer {settings.linkedin_access_token}",
                    "Content-Type": mime_type,
                },
            )
            _ensure_success(resp, "uploading the image to LinkedIn")
            print(f"📦 LinkedIn image uploaded: {image_urn}")

            # Step 3: Create the post
            resp = client.post(
                f"{API_BASE}/posts",
                json={
                    "author": org_urn,
                    "commentary": commentary,
                    "visibility": "PUBLIC",
                    "distribution": {
                        "feedDistribution": "MAIN_FEED",
                        "targetEntities": [],
                        "thirdPartyDistributionChannels": [],
                    },
                    "content": {"media": {"id": image_urn}},
                    "lifecycleState": "PUBLISHED",
                    "isReshareDisabledByAuthor": False,
                },
                headers=_headers(settings.linkedin_access_token),
            )
            _ensure_success(resp, "creating the LinkedIn post")

            post_urn = resp.headers.get("x-restli-id", "")
            if not post_urn:
                raise LinkedInPublishError("LinkedIn returned no post URN")

            print(f"✅ Published to LinkedIn! Post URN: {post_urn}")
            return post_urn
    except LinkedInPublishError:
        raise
    except httpx.HTTPError as exc:
        raise LinkedInPublishError("LinkedIn API request failed") from exc


def is_configured() -> bool:
    """Whether LinkedIn publishing credentials are present."""
    settings = get_settings()
    return bool(settings.linkedin_access_token and settings.linkedin_organization_id)


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _escape_commentary(text: str) -> str:
    """
    Escape LinkedIn "little text" control characters in commentary.

    # and @ are deliberately left unescaped so hashtags keep working.
    """
    for ch in "\\|{}[]()<>*_~":
        text = text.replace(ch, "\\" + ch)
    return text


def _ensure_success(response: httpx.Response, action: str):
    """Raise a safe error that never includes the access token."""
    if response.is_success:
        return
    try:
        message = response.json().get("message")
    except ValueError:
        message = None
    detail = message or f"HTTP {response.status_code}"
    raise LinkedInPublishError(f"LinkedIn failed while {action}: {detail}")


def validate_credentials() -> bool:
    """Check if the LinkedIn token can see the configured organization."""
    settings = get_settings()

    if not settings.linkedin_access_token or not settings.linkedin_organization_id:
        return False

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{API_BASE}/organizations/{settings.linkedin_organization_id}",
                headers=_headers(settings.linkedin_access_token),
            )
            data = resp.json()
            if resp.is_success and "localizedName" in data:
                print(f"✅ LinkedIn connected: {data['localizedName']}")
                return True
            print(f"❌ LinkedIn validation failed: {data}")
            return False
    except (httpx.HTTPError, ValueError) as e:
        print(f"❌ LinkedIn validation error: {e}")
        return False
