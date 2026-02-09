"""Content generator using Claude API to create posts in Nitesh's voice."""

import json
import random
import secrets
from pathlib import Path

import anthropic
from anthropic.types import MessageParam

from .config import get_settings
from .style_guide import NITESH_STYLE_SYSTEM_PROMPT, CONTENT_GENERATION_PROMPT
from .database import create_post, get_used_theme_ids


THEMES_PATH = Path(__file__).parent.parent / "config" / "content_themes.json"


def load_themes() -> list[dict]:
    """Load content themes from the configuration."""
    with open(THEMES_PATH) as f:
        data = json.load(f)
    return data["themes"]


def pick_theme() -> dict:
    """Pick a theme that hasn't been used recently."""
    themes = load_themes()
    used_ids = get_used_theme_ids(days=14)  # Avoid repeating within 2 weeks

    available = [t for t in themes if t["id"] not in used_ids]
    if not available:
        # All themes used recently, pick from the least recent
        available = themes

    return random.choice(available)


def generate_post(theme: dict | None = None) -> dict:
    """
    Generate a new Instagram post using Claude API.
    
    Returns the post-data dict with all fields, plus the database post_id.
    """
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    if theme is None:
        theme = pick_theme()

    prompt = CONTENT_GENERATION_PROMPT.format(
        theme=theme["theme"], context=theme["context"]
    )

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        system=NITESH_STYLE_SYSTEM_PROMPT,
        messages=[MessageParam(role="user", content=prompt)],
    )

    # Track token usage and cost
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    # Claude Sonnet 4.5 pricing: $3/MTok input, $15/MTok output
    cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    cost_inr = cost_usd * 85  # Approximate USD to INR

    usage_info = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 6),
        "cost_inr": round(cost_inr, 4),
        "model": "claude-sonnet-4-5-20250929",
    }
    print(f"💰 Cost: ${cost_usd:.6f} (₹{cost_inr:.4f}) | Tokens: {input_tokens} in / {output_tokens} out")

    # Parse the JSON response
    raw_text = response.content[0].text.strip()

    # Handle potential Markdown code fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

    post_data = json.loads(raw_text)

    # Generate a secure approval token
    approval_token = secrets.token_urlsafe(32)

    # Store in database
    # Store in a database
    post_id = create_post(
        theme_id=theme["id"],
        theme=theme["theme"],
        hook=post_data.get("hook", ""),
        caption=post_data.get("caption", ""),
        hashtags=post_data.get("hashtags", ""),
        alt_text=post_data.get("alt_text", ""),
        image_prompt=post_data.get("image_prompt", ""),
        cta=post_data.get("cta", ""),
        approval_token=approval_token,
        metadata=json.dumps(usage_info),
    )

    return {
        "post_id": post_id,
        "approval_token": approval_token,
        "cost": usage_info,
        **post_data,
    }


# CLI entry point
if __name__ == "__main__":
    import sys

    print("🧘 Generating a mindfulness post for teenagers...\n")

    try:
        post = generate_post()
        print(f"✅ Post #{post['post_id']} generated!\n")
        print(f"📌 Theme: {post.get('theme', 'N/A')}")
        print(f"🪝 Hook: {post.get('hook', 'N/A')}\n")
        print(f"📝 Caption:\n{post.get('caption', 'N/A')}\n")
        print(f"#️⃣  Hashtags: {post.get('hashtags', 'N/A')}\n")
        print(f"🖼️  Image idea: {post.get('image_prompt', 'N/A')}")
    except Exception as e:
        print(f"❌ Error generating post: {e}", file=sys.stderr)
        sys.exit(1)
