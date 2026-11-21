"""
main.py — Epic Games ULP Checker Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run:  python main.py
Env:  TG_BOT_TOKEN=your_token  (or edit config.py directly)

Install deps:
  pip install python-telegram-bot requests
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import BOT_TOKEN, THREADS
from bot    import build_app


# ── tiny health server so Render web service stops complaining ────────────────

class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *a):   # silence access logs
        pass

def _start_health_server():
    port = int(os.getenv("PORT", "10000"))
    srv  = HTTPServer(("0.0.0.0", port), _Health)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[*] Health check listening on port {port}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("[!] Set your bot token in config.py or via TG_BOT_TOKEN env var")
        return

    _start_health_server()

    app = build_app()
    print(f"[*] Epic checker bot running | {THREADS} threads")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
