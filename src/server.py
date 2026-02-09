"""
FastAPI server for the approval workflow.

Endpoints:
- GET /approve/{token}   — Approve and publish a post
- GET /reject/{token}    — Reject a post
- GET /preview/{token}   — Preview a post in browser
- GET /dashboard         — View recent posts and their statuses
- POST /generate         — Trigger manual post generation (API key protected)
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from .config import get_settings
from .database import (
    get_post_by_token,
    get_recent_posts,
    update_post_status,
    PostStatus,
)
from .instagram import publish_post, InstagramPublishError

app = FastAPI(
    title="Mindful Poster — Approval Server",
    description="Approval workflow for The Mindful Initiative's Instagram content",
    version="1.0.0",
)


# ─── Approval ────────────────────────────────────────────────────────────────

@app.get("/approve/{token}")
async def approve_post(token: str):
    """Approve a post and trigger Instagram publishing."""
    post = get_post_by_token(token)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post["status"] == PostStatus.PUBLISHED:
        return HTMLResponse(_result_page(
            "Already Published ✅",
            "This post has already been published to Instagram.",
            "#2e7d32",
        ))

    if post["status"] == PostStatus.REJECTED:
        return HTMLResponse(_result_page(
            "Previously Rejected",
            "This post was already rejected. Generate a new one if needed.",
            "#f57c00",
        ))

    # Mark as approved
    update_post_status(post["id"], PostStatus.APPROVED)

    # Try to publish to Instagram
    # Try to publish to Instagram
    try:
        # Placeholder image for testing — replace with real image generation later
        placeholder_image = "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=1080&q=80"

        instagram_post_id = publish_post(
            caption=post["caption"],
            hashtags=post["hashtags"],
            image_url=placeholder_image,
        )
        update_post_status(post["id"], PostStatus.PUBLISHED, instagram_post_id=instagram_post_id)

        return HTMLResponse(_result_page(
            "Post Published! 🧘",
            f"The post has been approved and published to Instagram!<br><br>"
            f"<em>Theme: {post['theme']}</em><br>"
            f"<em>Instagram Post ID: {instagram_post_id}</em>",
            "#2e7d32",
        ))

    except InstagramPublishError as e:
        update_post_status(post["id"], PostStatus.FAILED)
        return HTMLResponse(_result_page(
            "Publishing Failed ❌",
            f"The post was approved but publishing failed: {e}<br>Please try again or publish manually.",
            "#c62828",
        ))


# ─── Rejection ───────────────────────────────────────────────────────────────

@app.get("/reject/{token}")
async def reject_post(token: str):
    """Reject a post."""
    post = get_post_by_token(token)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post["status"] in (PostStatus.PUBLISHED, PostStatus.APPROVED):
        return HTMLResponse(_result_page(
            "Cannot Reject",
            "This post has already been approved/published.",
            "#f57c00",
        ))

    update_post_status(post["id"], PostStatus.REJECTED, rejection_reason="Rejected via email")
    return HTMLResponse(_result_page(
        "Post Rejected",
        "The post has been rejected. A new post will be generated in the next cycle.<br><br>"
        f"<em>Rejected theme: {post['theme']}</em>",
        "#c62828",
    ))


# ─── Preview ─────────────────────────────────────────────────────────────────

@app.get("/preview/{token}")
async def preview_post(token: str):
    """Preview a post in the browser (Instagram card style)."""
    post = get_post_by_token(token)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    settings = get_settings()
    base = settings.server_base_url.rstrip("/")

    status_badge = {
        PostStatus.PENDING_APPROVAL: ("🟡 Pending Review", "#f57c00"),
        PostStatus.APPROVED: ("🟢 Approved", "#2e7d32"),
        PostStatus.PUBLISHED: ("✅ Published", "#1565c0"),
        PostStatus.REJECTED: ("🔴 Rejected", "#c62828"),
        PostStatus.FAILED: ("❌ Failed", "#c62828"),
    }.get(post["status"], ("⚪ Draft", "#999"))

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Post Preview — The Mindful Initiative</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f0eb; padding: 20px; }}
        .container {{ max-width: 500px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 24px 0; }}
        .header h1 {{ color: #1a3a2a; font-size: 18px; letter-spacing: 1px; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; color: white; background: {status_badge[1]}; margin: 8px 0; }}
        .card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        .card-header {{ padding: 12px 16px; border-bottom: 1px solid #efefef; font-weight: 600; font-size: 14px; }}
        .card-image {{ background: linear-gradient(135deg, #1a3a2a, #3a7a52); padding: 48px 24px; text-align: center; }}
        .card-image p {{ color: #e8dfd6; font-size: 20px; font-style: italic; line-height: 1.5; }}
        .card-image .suggestion {{ color: #a8c4b0; font-size: 11px; margin-top: 16px; letter-spacing: 0.5px; }}
        .card-body {{ padding: 16px; }}
        .caption {{ font-size: 14px; line-height: 1.7; color: #262626; white-space: pre-line; }}
        .hashtags {{ color: #0095f6; font-size: 13px; margin-top: 12px; }}
        .meta {{ padding: 16px; background: #fafafa; border-top: 1px solid #efefef; font-size: 12px; color: #888; }}
        .actions {{ text-align: center; padding: 24px 0; }}
        .btn {{ display: inline-block; padding: 12px 32px; border-radius: 8px; font-size: 14px; font-weight: 600; text-decoration: none; margin: 4px; }}
        .btn-approve {{ background: #2e7d32; color: white; }}
        .btn-reject {{ background: #c62828; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧘 THE MINDFUL INITIATIVE</h1>
            <span class="status">{status_badge[0]}</span>
            <p style="font-size: 13px; color: #888; margin-top: 8px;">📌 {post['theme']}</p>
        </div>
        
        <div class="card">
            <div class="card-header">@themindfulinitiative</div>
            <div class="card-image">
                <p>"{post['hook']}"</p>
                <p class="suggestion">🖼️ {post['image_prompt']}</p>
            </div>
            <div class="card-body">
                <p class="caption">{post['caption']}</p>
                <p class="hashtags">{post['hashtags']}</p>
            </div>
            <div class="meta">
                <p>💡 CTA: {post['cta']}</p>
                <p style="margin-top: 4px;">♿ Alt text: {post['alt_text']}</p>
                <p style="margin-top: 4px;">📅 Created: {post['created_at']}</p>
            </div>
        </div>
        
        {"" if post["status"] != PostStatus.PENDING_APPROVAL else f'''
        <div class="actions">
            <a href="{base}/approve/{token}" class="btn btn-approve">✅ Approve & Publish</a>
            <a href="{base}/reject/{token}" class="btn btn-reject">❌ Reject</a>
        </div>
        '''}
    </div>
</body>
</html>"""
    return HTMLResponse(html)


# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.get("/dashboard")
async def dashboard():
    """Simple dashboard showing recent posts."""
    posts = get_recent_posts(limit=20)
    settings = get_settings()
    base = settings.server_base_url.rstrip("/")

    rows = ""
    for p in posts:
        status_emoji = {
            "pending_approval": "🟡",
            "approved": "🟢",
            "published": "✅",
            "rejected": "🔴",
            "failed": "❌",
            "draft": "⚪",
        }.get(p["status"], "⚪")

        rows += f"""
        <tr>
            <td>{p['id']}</td>
            <td>{status_emoji} {p['status']}</td>
            <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{p['theme']}</td>
            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{p['hook']}</td>
            <td>{p['created_at'][:10]}</td>
            <td><a href="{base}/preview/{p['approval_token']}">Preview</a></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Dashboard — Mindful Poster</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; padding: 32px; background: #f5f0eb; }}
        h1 {{ color: #1a3a2a; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        th {{ background: #1a3a2a; color: white; padding: 12px; text-align: left; font-size: 13px; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 13px; }}
        tr:hover {{ background: #f9f6f2; }}
        a {{ color: #0095f6; }}
    </style>
</head>
<body>
    <h1>🧘 Mindful Poster — Dashboard</h1>
    <table>
        <thead>
            <tr><th>#</th><th>Status</th><th>Theme</th><th>Hook</th><th>Date</th><th>Preview</th></tr>
        </thead>
        <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center; padding: 24px; color: #999;">No posts yet. Generate your first post!</td></tr>'}</tbody>
    </table>
</body>
</html>"""
    return HTMLResponse(html)


# ─── Manual Generation Trigger ───────────────────────────────────────────────

@app.post("/generate")
async def trigger_generation(request: Request):
    """Manually trigger a new post generation. Protected by API key."""
    settings = get_settings()
    
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {settings.secret_key}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    from .generator import generate_post
    from .emailer import send_approval_email

    post_data = generate_post()
    send_approval_email(post_data)

    return {
        "message": "Post generated and approval email sent",
        "post_id": post_data["post_id"],
        "theme": post_data.get("theme", ""),
        "hook": post_data.get("hook", ""),
    }


# ─── Health Check ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mindful-poster"}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _result_page(title: str, message: str, color: str) -> str:
    """Generate a simple result page HTML."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Mindful Poster</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #f5f0eb; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: white; border-radius: 16px; padding: 48px; max-width: 480px; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
        h1 {{ color: {color}; font-size: 24px; margin-bottom: 16px; }}
        p {{ color: #555; line-height: 1.6; font-size: 15px; }}
        a {{ color: #0095f6; margin-top: 16px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>{title}</h1>
        <p>{message}</p>
        <a href="/dashboard">← Back to Dashboard</a>
    </div>
</body>
</html>"""


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    settings = get_settings()
    print(f"🧘 Mindful Poster server starting on port {settings.server_port}...")
    uvicorn.run(app, host="0.0.0.0", port=settings.server_port)
