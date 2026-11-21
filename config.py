"""
config.py — Epic Checker Bot settings
"""
import os

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ── Threading ─────────────────────────────────────────────────────────────────
THREADS     = 40
TIMEOUT     = 12          # seconds per request
MAX_RETRIES = 2           # times to re-check RETRY combos before giving up

# ── Epic Games OAuth (EGL launcher client creds) ──────────────────────────────
EPIC_TOKEN_URL = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
EPIC_AUTH      = (
    "Basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRhYzFjYTY6"
    "OTIwOWQ0YTUtZTI4NS00ZTY5LWFiMjMtNjMzMDc5OGMzMWI1"
)
EPIC_HEADERS = {
    "Authorization": EPIC_AUTH,
    "Content-Type":  "application/x-www-form-urlencoded",
    "User-Agent":    "EpicGamesLauncher/15.17.1-23833206+++Portal+Release-Live Windows/10.0.19043.1.256.64bit",
    "Accept":        "application/json",
}

# error code → result label
ERR_MAP = {
    "errors.com.epicgames.account.invalid_account_credentials":          "BAD",
    "errors.com.epicgames.account.account_not_found":                    "DEAD",
    "errors.com.epicgames.common.two_factor_authentication.required":    "2FA",
    "errors.com.epicgames.account.account_not_active":                   "DEAD",
    "errors.com.epicgames.common.throttled":                             "RETRY",
}

# ULP domain filter
EPIC_DOMAINS = {
    "epicgames.com", "epicgames", "fortnite.com",
    "unrealengine.com", "epicgames.net",
}

# ── ghostproxies.net gateway ──────────────────────────────────────────────────
# ghostproxies.net is a GATEWAY service, not a proxy list.
# All requests route through gate.ghostproxies.net:8080 — no list to download.
#
# To use:
#   Option A (recommended): set GHOST_KEY env var in Render dashboard
#   Option B (local only):  replace PASTE_YOUR_KEY_HERE below with your key
#
# Get your API key from: https://ghostproxies.net/dashboard
#
GHOST_KEY  = os.getenv("GHOST_KEY",  "PASTE_YOUR_KEY_HERE")
GHOST_USER = os.getenv("GHOST_USER", "res-any")   # res-any / res-us / res-in / etc.
GHOST_HOST = "gate.ghostproxies.net:8080"
