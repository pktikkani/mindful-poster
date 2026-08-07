"""One-shot LinkedIn OAuth: opens the browser, catches the callback, prints the token.

Run:  python scripts/linkedin_auth.py
Needs LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env.
Log into linkedin.com in your browser as the mTeen Wellness page admin first.
"""

import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import dotenv_values

PORT = 8912
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPE = "w_organization_social"

env = dotenv_values(Path(__file__).parent.parent / ".env")
CLIENT_ID = env.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = env.get("LINKEDIN_CLIENT_SECRET", "")
if not CLIENT_ID or not CLIENT_SECRET:
    sys.exit("Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env first.")

state = secrets.token_urlsafe(16)
result: dict = {}


class Callback(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = parse_qs(parsed.query)
        if params.get("state", [""])[0] != state:
            body = "State mismatch — close this tab and rerun the script."
        elif "error" in params:
            result["error"] = f"{params['error'][0]}: {params.get('error_description', [''])[0]}"
            body = f"LinkedIn returned an error: {result['error']}"
        else:
            result["code"] = params.get("code", [""])[0]
            body = "✅ Authorized — you can close this tab and return to the terminal."
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<h2>{body}</h2>".encode())
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args):
        pass


auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode({
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "state": state,
})

server = HTTPServer(("localhost", PORT), Callback)
print("Opening LinkedIn authorization in your browser…")
print(f"If it doesn't open, visit:\n\n{auth_url}\n")
webbrowser.open(auth_url)
server.serve_forever()

if "error" in result:
    sys.exit(f"Authorization failed: {result['error']}")
if not result.get("code"):
    sys.exit("No authorization code received.")

resp = httpx.post(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data={
        "grant_type": "authorization_code",
        "code": result["code"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    },
    timeout=30,
)
data = resp.json()
if "access_token" not in data:
    sys.exit(f"Token exchange failed: {data}")

days = data.get("expires_in", 0) // 86400
print(f"\n✅ Access token (valid ~{days} days) — add this line to .env:\n")
print(f"LINKEDIN_ACCESS_TOKEN={data['access_token']}")
