# STATUS — 2026-08-05

## Last session outcome
- Post 17 published to Instagram (IG post ID `18100645964630953`).
- Post 18 ("First Heartbreak"): approved by Nitesh, publish failed on the tunnel-domain issue; per Pavan, left **unpublished** intentionally.
- **Fix shipped (uncommitted)**: `src/media.py` + `src/server.py` — when `SERVER_BASE_URL` is a tunnel/localhost host (`is_meta_blocked_host`), the approve flow re-hosts the exact stored image via `upload_for_meta()` (catbox.moe) before calling Instagram. Dry-run verified: container creation 200 with re-hosted URL.
- Post 19 ("10 minutes outside resets your mind") generated and emailed to Nitesh for approval — his Approve click should now publish end-to-end.
- **Stories added (uncommitted)**: Approve now also publishes a 9:16 story derived from the exact approved image (blurred backdrop, `compose_story_card` in `image_generator.py`; `publish_story` in `instagram.py`; wired non-fatally in the approve flow — a story failure never undoes the live feed post). Dry-run verified: STORIES container 200. Story image is derived at publish time, not stored in DB.
- Approval email goes to nitesh.batra@gmail.com (`APPROVAL_EMAIL` in `.env`).

## Key finding (blocks future publishes)
**Meta rejects tunnel domains as `image_url`** (`trycloudflare.com`, `ngrok-free.app`) with error 9004 / subcode 2207052 "Only photo or video can be accepted as media type" — it won't even fetch the image. Verified: same account/token succeeds instantly with a normal public image URL. ngrok free additionally serves an HTML interstitial to browser UAs.

Workaround used: uploaded the exact approved JPEG to catbox.moe and called `publish_post()` directly with that URL, then `update_post_status(..., PUBLISHED)`.

## Running processes (this machine, will not survive reboot)
- uvicorn on :8000 (started with `env -u ANTHROPIC_API_KEY` — see below)
- ngrok tunnel `https://10f0-106-51-46-155.ngrok-free.app` (old email links)
- cloudflared quick tunnel `https://thriller-telling-healthy-visiting.trycloudflare.com` (current `SERVER_BASE_URL`)

## Gotcha
The shell used to launch the server can carry an **empty** `ANTHROPIC_API_KEY` env var that overrides `.env` (pydantic-settings precedence) → "ANTHROPIC_API_KEY is not configured". Start the server with `env -u ANTHROPIC_API_KEY`.

## Next steps
1. **Deploy the server** (Railway/Render/Fly) with a real domain — fixes publish permanently; tunnels are only viable for the email-approval part, not for Instagram media fetch.
2. Until deployed, either keep the manual catbox re-host step, or add an upload-to-trusted-host step inside `publish_post`.
3. Orphan test containers were created during debugging (incl. one with a Wikipedia cat image) — never published, they expire in ~24h on their own.
