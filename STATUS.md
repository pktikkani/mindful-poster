# STATUS — 2026-08-12

## Last session outcome: Instagram 9004 bug fixed; publish path converted to native async; verified live twice
- **Final state (commit `9c77870`, deployed on Railway)**: `publish_post`/`publish_story`/`upload_for_meta` are async (`httpx.AsyncClient` + `asyncio.sleep`); approve handler is `async def` again; Pillow story composition and LinkedIn publish run via `run_in_threadpool`. Tests 10/10.
- **End-to-end verified in production twice**: post `FO1sIw…` (with sync-handler workaround `b2e06d0`) and post `8orKuLw…` (with full async `9c77870`) — feed + story both published via approval click; multi-approver "already published by X" attribution confirmed working with pavan@prag-matic.com added.

- **Production**: Railway, custom domain `https://mindful-poster.nubewired.com` (`SERVER_BASE_URL` set in Railway vars; vars only apply on redeploy). Verified live: post 18079290902687246 (feed) + story published via approval click.
- **Real root cause** (commit `b2e06d0`): the `POST /approve` handler was `async def` but called the blocking sync Graph API client, freezing the event loop — Meta's crawler then couldn't fetch `/media/{token}.jpg` *from the same server* mid-publish → error 9004 / subcode 2207052 "media could not be fetched". Handler is now sync (FastAPI threadpool). Signature to remember: publish fails from the server but the identical Graph call succeeds from any other machine; Meta's GET appears in logs *after* the error.
- **Secondary fixes** (commit `f294eca`, by Codex agent in herdr pane): stories are served first-party at `/media/{token}-story.jpg` (1080×1920 composed from the stored post image) when the host isn't Meta-blocked; catbox.moe (blocked by Meta) replaced with uguu.se as the tunnel/local-only fallback. Tests 10/10.
- Diagnostic logging added (`3b4536c`, `e0c996e`): prints exact `image_url`, account, token fingerprint, and full Graph error — keep, it's what cracked the case.
- Meta seems to **cache negative fetch results per URL** for a while — after fixing, a previously-failed post may need a retry or a fresh post.

## Env / config notes
- `.env.local` (hook-protected, Pavan edits by hand): `APPROVAL_EMAIL` still sanjay+nitesh — Pavan wanted pavan@prag-matic.com added for testing (done in Railway, NOT in local file yet).
- Railway `APPROVAL_EMAIL` now includes pavan@prag-matic.com.
- Security flags raised to Pavan: Neon DB URL briefly echoed in a herdr pane; `.env.local` holds live keys (OpenAI, Anthropic, Resend, Neon) — rotation advised, not done.

## Open issues
- Posts 20, 21 (and 27, `FO1sIw…` was retried to success) — older `failed` posts 20/21 still unexplained but almost certainly the same event-loop deadlock.
- `.env.example` still lacks the four LINKEDIN_* lines.
- LinkedIn: worked in earlier session per commit history; token expiry ~60 days from early Aug.

## Gotcha (still true)
Shell can carry an empty `ANTHROPIC_API_KEY` that overrides `.env` — start anything needing Claude with `env -u ANTHROPIC_API_KEY`.
