"""Email service for sending approval emails to Nitesh."""

from pathlib import Path
from urllib.parse import quote_plus

import resend
from jinja2 import Template

from .config import get_settings
from .media import public_image_url

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "approval_email.html"


def send_approval_email(post_data: dict) -> str:
    """
    Send an approval email with the post preview.
    
    Args:
        post_data: Dict containing post fields + post_id + approval_token
    
    Returns:
        The Resend email ID
    """
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")
    resend.api_key = settings.resend_api_key

    base = settings.server_base_url.rstrip("/")
    token = post_data["approval_token"]
    image_url = post_data.get("image_url") or public_image_url(base, token)
    template = Template(TEMPLATE_PATH.read_text())

    # Each approver gets their own links carrying their identity, so the
    # server can tell the second approver who already acted on the post.
    email_id = "unknown"
    for recipient in settings.approval_email_list:
        by = quote_plus(recipient)
        html_body = template.render(
            hook=post_data.get("hook", ""),
            caption=post_data.get("caption", ""),
            hashtags=post_data.get("hashtags", ""),
            image_prompt=post_data.get("image_prompt", ""),
            theme=post_data.get("theme", "Mindfulness"),
            cta=post_data.get("cta", ""),
            alt_text=post_data.get("alt_text", ""),
            approve_url=f"{base}/approve/{token}?by={by}",
            reject_url=f"{base}/reject/{token}?by={by}",
            preview_url=f"{base}/preview/{token}",
            revise_url=f"{base}/revise/{token}?by={by}",
            image_url=image_url,
        )

        response = resend.Emails.send(
            {
                "from": settings.from_email,
                "to": [recipient],
                "subject": f"🧘 New Mindful Post for Review — {post_data.get('theme', 'Mindfulness for Teens')}",
                "html": html_body,
            }
        )

        email_id = response.get("id", "unknown") if isinstance(response, dict) else getattr(response, "id", "unknown")
        print(f"📧 Approval email sent to {recipient} (ID: {email_id})")
    return email_id
