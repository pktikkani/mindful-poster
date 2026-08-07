# STATUS — 2026-08-07

## Last session outcome: LinkedIn cross-posting built, waiting on LinkedIn approval
- **LinkedIn publishing wired in (committed & pushed to main)**: Approve now also posts to the mTeen Wellness company page (`linkedin.com/company/mteen-wellness`), non-fatally — a LinkedIn failure never affects the live IG post (same pattern as stories).
  - `src/linkedin.py` (new): Posts API — image goes up as a **direct binary upload**, so the Meta tunnel-domain problem does not apply to LinkedIn. Includes `validate_credentials()`.
  - LinkedIn text is a **separate generated variant**, not the IG caption: `generate_linkedin_caption()` in `generator.py` + `LINKEDIN_ADAPTATION_PROMPT` in `style_guide.py` — professional-warm, written for parents/educators/counsellors, 3-5 hashtags. Stored in new `posts.linkedin_caption` column (auto-migrated via `_ensure_columns()` in `database.py`). Generation failure falls back to IG caption, never blocks the pipeline.
  - Approval email now shows both versions (LinkedIn card in `templates/approval_email.html`); one Approve publishes IG feed + story + LinkedIn.
  - Approve flow skips LinkedIn silently until `LINKEDIN_ACCESS_TOKEN` + `LINKEDIN_ORGANIZATION_ID` are set in `.env`.
- **Test preview sent** to pavan@prag-matic.com only (Resend `ef1eec0b…`): post 19's image with IG caption vs generated LinkedIn version. Post 19's `linkedin_caption` backfilled in DB. Nothing published; Nitesh not emailed.
- All 8 tests pass.

## LinkedIn setup — where it stands (BLOCKED on LinkedIn review, a few days)
Done today: app "mTeen Poster" created on developer.linkedin.com (client id `86ks9hjdrr488o`), associated + **verified** with the mTeen Wellness page, redirect URL `http://localhost:8912/callback` added, `LINKEDIN_CLIENT_ID`/`LINKEDIN_CLIENT_SECRET` in `.env`, Community Management API **access request form submitted** (use case: Page management only).

Key learning: even the **Development tier requires the access form + review** (verified business email, registered legal org, website, privacy policy). Until approved, `w_organization_social` is missing from the Auth tab and OAuth fails with `invalid_scope_error` — that's the observed state, not a bug.

### When approval email arrives
1. `! .venv/bin/python scripts/linkedin_auth.py` (browser Allow as page admin) → paste printed `LINKEDIN_ACCESS_TOKEN=…` into `.env` (token ~60 days).
2. Ensure `LINKEDIN_ORGANIZATION_ID=<numeric id>` in `.env` (from page admin URL `linkedin.com/company/<number>/admin/…`) — Pavan may have done this already.
3. Validate: `.venv/bin/python -c "from src.linkedin import validate_credentials; validate_credentials()"`.
4. Restart uvicorn (running server has pre-LinkedIn code).

## Open issues
- **Posts 20 and 21 are `failed`** (approved, publish failed sometime after Aug 5) — not investigated; flagged to Pavan, no answer yet.
- Cloudflare tunnel from Aug 5 is **dead**; no server/tunnel currently running. Deploy to a real domain is still next step #1 (fixes IG tunnel-block permanently; LinkedIn doesn't care either way).
- `.env`/`.env.example` edits are blocked by the user's protect-paths hook — Pavan edits those by hand. `.env.example` still lacks the four LINKEDIN_* lines.

## Gotcha (still true)
Shell can carry an empty `ANTHROPIC_API_KEY` that overrides `.env` — start anything needing Claude with `env -u ANTHROPIC_API_KEY`.
