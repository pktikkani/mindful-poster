# 🧘 Mindful Poster — AI-Powered Social Media for The Mindful Initiative

An automated content pipeline that generates mindfulness posts for teenagers in **Nitesh Batra's** authentic voice, sends them for approval via email, and publishes approved posts to Instagram.

Built by [Prag-Matic (Nubewired Software Technologies)](https://prag-matic.com) for [The Mindful Initiative](https://themindfulinitiative.com).

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌───────────┐
│  Scheduler   │────▶│ Claude API   │────▶│ Email with  │────▶│ Instagram │
│  (Daily 7AM) │     │ (Sonnet 4.5) │     │ Approve/    │     │ Graph API │
│              │     │              │     │ Reject)     │     │ (Publish) │
└─────────────┘     └──────────────┘     └─────┬───────┘     └───────────┘
                                               │
                                        Nitesh clicks
                                        Approve/Reject
                                               │
                                        ┌──────▼───────┐
                                        │  FastAPI      │
                                        │  Webhook      │
                                        │  Server       │
                                        └──────────────┘
```

## How It Works

1. **Daily Generation**: A scheduled job (7 AM IST) triggers Claude API to generate an Instagram post about mindfulness for teenagers, written in Nitesh's storytelling style.
2. **Email for Review**: The generated post is emailed to Nitesh with a preview, along with **Approve** and **Reject** buttons.
3. **Approval Webhook**: When Nitesh clicks "Approve", the FastAPI server receives the request and triggers Instagram publishing.
4. **Instagram Publishing**: The approved post is published via Instagram Graph API.

## Cost

- ~₹1.27 per post using Claude Sonnet 4.5
- ~₹38/month for 1 post/day
- Cost tracked per post in the database (input tokens, output tokens, USD, INR)

---

## Tech Stack

- **Python 3.11+**
- **FastAPI** — Webhook server for approval/rejection
- **Anthropic SDK** — Content generation via Claude Sonnet 4.5
- **Resend** — Transactional emails
- **Instagram Graph API** — Publishing to Instagram
- **SQLite** — Lightweight post tracking database
- **APScheduler** — Job scheduling

---

## Setup

### Prerequisites

You'll need accounts and API keys for:
- **Anthropic API** → https://console.anthropic.com
- **Resend** → https://resend.com
- **Instagram Graph API** → Requires Facebook Developer account + Instagram Professional account

---

### Step 1: Clone & Install

```bash
cd mindful-poster
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Step 2: Anthropic API Key

1. Go to https://console.anthropic.com/settings/keys
2. Create a new key (starts with `sk-ant-`)
3. Either add to `.env` or export in your shell profile:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-xxxxx
   ```

---

### Step 3: Resend Setup (Email)

1. Sign up at https://resend.com (free tier: 100 emails/day)
2. Go to **Domains** → **Add Domain** → Enter your domain (e.g. `prag-matic.com`)
3. Add the DNS records Resend provides (SPF, DKIM, MX) to your DNS provider
4. Wait for verification (5 min to a few hours)
5. Go to **API Keys** → **Create API Key**
   - Name: `mindful-poster`
   - Permission: Sending access
   - Domain: Select your verified domain
6. Copy the key (starts with `re_`)

---

### Step 4: Instagram Graph API Setup

This is the most involved step. Follow carefully.

#### 4a. Switch Instagram to Business Account

1. Open Instagram **mobile app** (can't do this on web)
2. Go to your profile → ☰ → Settings and privacy
3. Account type and tools → **Switch to Professional Account**
4. Select **Business** → Pick any category → Done

#### 4b. Connect Instagram to a Facebook Page

1. Go to your Facebook Page (e.g. https://www.facebook.com/YourPage)
2. Page Settings → Linked Accounts → Connect Instagram
3. Log in with your Instagram credentials

#### 4c. Create a Facebook App

1. Go to https://developers.facebook.com
2. Click **My Apps** → **Create App**
3. Select **"Content management"** use case
4. Name it (e.g. `Mindful Poster`)
5. Skip business portfolio for now: select **"I don't want to connect a business portfolio yet."**
6. Click **Create**

#### 4d. Add Required Permissions

1. In the app dashboard, go to **Use cases** → click on **"Manage messaging & content on Instagram"**
2. Click **"Permissions and features"** in the left sidebar
3. Make sure these are **"Ready for testing"**:
   - `instagram_business_basic`
   - `instagram_business_content_publish`
   - `instagram_content_publish`
   - `instagram_manage_comments`
4. Click **"+ Add"** for any that aren't listed

#### 4e. Add Instagram Tester

1. In the app dashboard, go to **App roles** (left sidebar, near bottom)
2. Click **Roles** → **Add People**
3. Add your Instagram username as an **Instagram Tester**
4. Open Instagram **mobile app** → Settings → Website permissions → Tester invitations → **Accept**

#### 4f. Generate Access Token

1. Go back to **Use cases** → **Customize** → **API setup with Instagram login**
2. Under section **2. Generate access tokens**, click **"Add account"**
3. Connect your Instagram account and authorize
4. **Copy the token immediately** — it's only shown once!
5. Save it to your `.env` as `INSTAGRAM_ACCESS_TOKEN`

#### 4g. Get Instagram Account ID

Run this in your terminal (replace with your actual token):

```bash
curl "https://graph.instagram.com/me?fields=id,username&access_token=YOUR_TOKEN_HERE"
```

Response:
```json
{
  "id": "12345678901234567",
  "username": "your_username"
}
```

The `id` value is your `INSTAGRAM_ACCOUNT_ID`.

---

### Step 5: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Anthropic API (can also be in shell profile)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Resend (Email)
RESEND_API_KEY=re_xxxxx
FROM_EMAIL=yourname@yourdomain.com
APPROVAL_EMAIL=recipient@example.com

# Instagram Graph API
INSTAGRAM_ACCESS_TOKEN=your_instagram_token
INSTAGRAM_ACCOUNT_ID=your_instagram_account_id

# Server
SERVER_BASE_URL=http://localhost:8000
SERVER_PORT=8000
SECRET_KEY=generate-a-random-string-here

# Scheduler
POST_GENERATION_HOUR=7
POST_GENERATION_MINUTE=0
TIMEZONE=Asia/Kolkata
```

---

### Step 6: Test

Start the server:

```bash
python -m src.server
```

In another terminal, trigger a test post:

```bash
curl -X POST http://localhost:8000/generate \
  -H "Authorization: Bearer your-secret-key-here"
```

You should see:
1. **Terminal**: Cost info (`💰 Cost: $0.01 (₹1.27)`) and email confirmation
2. **Email**: Approval email with post preview and Approve/Reject buttons
3. **Click Approve**: Post publishes to Instagram

### Step 7: Dashboard

View all generated posts and their statuses:

```
http://localhost:8000/dashboard
```

---

## Running in Production

### Daily Scheduler

Use the built-in scheduler for automated daily generation:

```bash
python -m src.scheduler
```

This generates a post at the configured time (default: 7 AM IST) and sends the approval email.

### Deploying the Server

The FastAPI server must be publicly accessible for the email approval links to work. Deploy to any cloud provider:

- **Railway**: https://railway.app
- **Render**: https://render.com
- **Fly.io**: https://fly.io
- **Your own VPS**

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000
```

Update `SERVER_BASE_URL` in `.env` to your public URL after deploying.

### Instagram Token Refresh

The Instagram access token expires in **60 days**. You'll need to regenerate it by repeating Step 4f. A future enhancement could add automatic token refresh.

---

## Project Structure

```
mindful-poster/
├── src/
│   ├── __init__.py          # Package init
│   ├── config.py            # Environment config (pydantic-settings)
│   ├── database.py          # SQLite database operations
│   ├── generator.py         # Claude API content generation + cost tracking
│   ├── emailer.py           # Resend email with approval links
│   ├── instagram.py         # Instagram Graph API publisher
│   ├── server.py            # FastAPI webhook server + dashboard
│   ├── scheduler.py         # APScheduler for daily generation
│   └── style_guide.py       # Nitesh's writing style prompt
├── templates/
│   └── approval_email.html  # Email template (Jinja2)
├── config/
│   └── content_themes.json  # 20 teen mindfulness themes
├── data/
│   └── posts.db             # SQLite database (auto-created)
├── .env.example             # Environment template
├── .env                     # Your actual config (git-ignored)
├── requirements.txt         # Python dependencies
└── README.md
```

## Content Themes

The generator rotates through 20 teenager-relevant mindfulness themes to avoid repetition:

- Exam stress & performance anxiety
- Social media comparison
- Friendship conflicts & feeling left out
- Breath awareness (2-minute reset)
- Identity beyond grades & looks
- Anger management (the mindful pause)
- Sleep & rest (screens don't count)
- Parent expectations
- Self-compassion when you mess up
- Body image
- Gratitude practice (3 good things)
- Peer pressure (saying no)
- First heartbreak
- Nature connection (10 min outside)
- Digital detox
- Morning intention (Sankalpa)
- Deep listening
- Embracing imperfection
- Movement as meditation
- Compassion for others

Themes are defined in `config/content_themes.json` and can be customized.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|---|---|
| `ImportError: attempted relative import` | Run with `python -m src.server` not `python src/server.py` |
| `anthropic.NotFoundError: model not found` | Check model string is `claude-sonnet-4-5-20250929` |
| `Instagram: Invalid OAuth access token` | Token expired — regenerate via Step 4f |
| `Instagram: Insufficient Developer Role` | Accept tester invite on Instagram app (Step 4e) |
| `Resend: can only send to verified email` | Verify your domain in Resend (Step 3) or use your own email for testing |
| `sqlite3 errors on schema` | Delete `data/posts.db` and restart — schema will recreate |

### PyCharm Warnings

These are IDE warnings, not real errors:
- **SQL dialect warnings**: Settings → Languages & Frameworks → SQL Dialects → set to SQLite
- **`MessageParam` type warning**: Add `# type: ignore` or use `from anthropic.types import MessageParam`

---

## Future Enhancements

- [ ] AI image generation (DALL-E / Stability AI) for each post
- [ ] Automatic Instagram token refresh before expiry
- [ ] Multi-platform support (LinkedIn, Twitter/X)
- [ ] A/B testing of post variations
- [ ] Analytics tracking (engagement metrics)
- [ ] Deploy to cloud with auto-scheduler
- [ ] Admin web UI for theme management

---

## About

**The Mindful Initiative** was founded by Nitesh Batra, India's first certified Compassion Cultivation Training (CCT) instructor from Stanford's CCARE. This tool supports his mission to bring mindfulness to teenagers through engaging, authentic social media content.

**Built by**: Prag-Matic (Nubewired Software Technologies Pvt Ltd)

## License

Private — Built for The Mindful Initiative by Prag-Matic.