"""
scraper.py — Scrape fresh proxies from public GitHub proxy lists
Fetches HTTP, SOCKS4, SOCKS5 from multiple sources and merges+dedupes them.
"""
import threading
import requests

# ── sources ───────────────────────────────────────────────────────────────────
# Each URL is a raw .txt with one  ip:port  per line.
SOURCES: dict[str, list[str]] = {
    "http": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    ],
    "socks4": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks4.txt",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks5.txt",
    ],
}

SCHEME_PREFIX = {
    "http":   "http://",
    "socks4": "socks4://",
    "socks5": "socks5://",
}

FETCH_TIMEOUT = 10   # seconds per URL


def _fetch_url(url: str, results: list, lock: threading.Lock):
    """Download one proxy list URL, append raw lines to results."""
    try:
        r = requests.get(url, timeout=FETCH_TIMEOUT)
        if r.status_code == 200:
            with lock:
                results.extend(r.text.splitlines())
    except Exception:
        pass   # silently skip dead sources


def _normalize(line: str, scheme: str) -> str | None:
    """
    Normalize a raw proxy line to scheme://ip:port.
    Accepts: ip:port  or  already-prefixed strings.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # strip existing scheme so we can re-prefix cleanly
    for pfx in ("http://", "https://", "socks4://", "socks5://"):
        if line.startswith(pfx):
            line = line[len(pfx):]
            break
    # must look like  host:port
    parts = line.rsplit(":", 1)
    if len(parts) != 2:
        return None
    host, port = parts
    if not port.isdigit():
        return None
    return f"{SCHEME_PREFIX[scheme]}{host}:{port}"


def scrape(
    types: list[str] | None = None,
    progress_cb=None,          # optional: (msg: str) → None
) -> tuple[list[str], dict[str, int]]:
    """
    Scrape proxies from all GitHub sources.

    Args:
        types:       list of types to scrape, e.g. ["http","socks5"].
                     None → scrape all 3.
        progress_cb: called with status strings during scrape.

    Returns:
        (proxy_list, counts)
        proxy_list — deduplicated list of  scheme://ip:port  strings
        counts     — {"http": N, "socks4": N, "socks5": N}
    """
    if types is None:
        types = list(SOURCES.keys())

    all_proxies: list[str] = []
    seen:  set[str]        = set()
    counts: dict[str, int] = {}

    for ptype in types:
        urls     = SOURCES.get(ptype, [])
        raw_lines: list[str] = []
        lock     = threading.Lock()
        threads  = []

        if progress_cb:
            progress_cb(f"🌐 Fetching {ptype.upper()} from {len(urls)} sources...")

        for url in urls:
            t = threading.Thread(target=_fetch_url, args=(url, raw_lines, lock), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        # normalize + dedupe
        type_count = 0
        for line in raw_lines:
            normalized = _normalize(line, ptype)
            if normalized and normalized not in seen:
                seen.add(normalized)
                all_proxies.append(normalized)
                type_count += 1

        counts[ptype] = type_count
        if progress_cb:
            progress_cb(f"✅ {ptype.upper()}: {type_count} unique proxies")

    return all_proxies, counts
