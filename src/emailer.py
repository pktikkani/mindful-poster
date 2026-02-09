"""Email service for sending approval emails to Nitesh."""

from pathlib import Path

import resend
from jinja2 import Template

from .config import get_settings

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
    resend.api_key = settings.resend_api_key

    # Build approval/reject URLs
    base = settings.server_base_url.rstrip("/")
    token = post_data["approval_token"]
    approve_url = f"{base}/approve/{token}"
    reject_url = f"{base}/reject/{token}"
    preview_url = f"{base}/preview/{token}"

    # Render the email template
    template_str = TEMPLATE_PATH.read_text()
    template = Template(template_str)
    html_body = template.render(
        hook=post_data.get("hook", ""),
        caption=post_data.get("caption", ""),
        hashtags=post_data.get("hashtags", ""),
        image_prompt=post_data.get("image_prompt", ""),
        theme=post_data.get("theme", "Mindfulness"),
        cta=post_data.get("cta", ""),
        alt_text=post_data.get("alt_text", ""),
        approve_url=approve_url,
        reject_url=reject_url,
        preview_url=preview_url,
    )

    # Send via Resend
    response = resend.Emails.send(
        {
            "from": settings.from_email,
            "to": [settings.approval_email],
            "subject": f"🧘 New Mindful Post for Review — {post_data.get('theme', 'Mindfulness for Teens')}",
            "html": html_body,
        }
    )

    email_id = response.get("id", "unknown") if isinstance(response, dict) else getattr(response, "id", "unknown")
    print(f"📧 Approval email sent to {settings.approval_email} (ID: {email_id})")
    return email_id
