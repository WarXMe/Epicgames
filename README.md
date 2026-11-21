<div align="center">

<img src="https://upload.wikimedia.org/wikipedia/commons/3/31/Epic_Games_logo.svg" width="80" alt="Epic Games"/>

# 🎮 Epic Games Checker

**A fast, multi-threaded Telegram bot for validating Epic Games accounts**

![Python](https://img.shields.io/badge/Python-3.11.9-blue?style=flat-square&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white)
![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat-square&logo=render&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

## ✨ Features

- 🚀 **Multi-threaded** — 40 concurrent threads, checks thousands of combos fast
- 🎯 **ULP + Combo** — supports both `url:email:pass` ULP files and plain `email:pass` combos
- 🛡️ **Captive Portal Protection** — validates real Epic token fields, zero fake hits
- 🔄 **Auto-retry** — throttled accounts are re-queued and rechecked automatically
- 🌐 **Proxy support** — load your own list, auto-scrape 19 public sources, or use ghostproxies.net gateway
- 📡 **Live validation** — scraped proxies are tested before use, dead ones dropped
- 📁 **File output** — HITS, 2FA, and RETRY results sent as `.txt` files

---

## 📊 Result Labels

| Label | Meaning |
|-------|---------|
| ✅ `HIT` | Valid account — correct email & password |
| 🔐 `2FA` | Valid account — blocked by two-factor auth |
| ❌ `BAD` | Wrong password |
| 💀 `DEAD` | Account not found or inactive |
| 🔁 `RETRY` | Throttled by Epic — auto re-queued |
| ⚠️ `ERROR` | Network error or dead proxy |

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome screen & mode selector |
| `/mode` | Switch between ULP and Combo mode |
| `/proxy` | Load proxies from a `.txt` file |
| `/proxies` | Show current proxy pool count |
| `/clearproxy` | Wipe loaded proxies |
| `/scrapeproxy` | Scrape 19 sources + validate live proxies |
| `/ghostproxy` | Show ghostproxies.net gateway status |

---

## 🚀 Setup

### 1. Clone & install

```bash
git clone https://github.com/WarXMe/Epicgames
cd Epicgames
pip install -r requirements.txt
```

### 2. Configure

Open `config.py` and set your values:

```python
# Telegram
BOT_TOKEN = "YOUR_BOT_TOKEN"       # from @BotFather

# ghostproxies.net (optional)
GHOST_KEY  = "YOUR_API_KEY"        # from ghostproxies.net dashboard
GHOST_USER = "res-any"             # res-any / res-us / res-in / etc.
```

### 3. Run

```bash
python main.py
```

---

## ☁️ Deploy on Render

1. Push repo to GitHub
2. Create a new **Background Worker** on [Render](https://render.com)
3. Set environment variables in **Dashboard → Environment**:

```
TG_BOT_TOKEN   →  your Telegram bot token
GHOST_KEY      →  your ghostproxies.net API key (optional)
GHOST_USER     →  res-any (optional, default)
```

4. Build command: `pip install -r requirements.txt`
5. Start command: `python main.py`

---

## 📂 File Structure

```
Epicgames/
├── main.py          # entry point
├── bot.py           # Telegram handlers & commands
├── checker.py       # Epic OAuth validator
├── engine.py        # threaded check runner
├── parser.py        # ULP / combo parser
├── proxy_pool.py    # thread-safe round-robin pool
├── scraper.py       # 19-source proxy scraper
├── validator.py     # live proxy tester
├── config.py        # settings & constants
├── render.yaml      # Render deployment config
└── requirements.txt
```

---

## 🌐 Proxy Support

| Method | How |
|--------|-----|
| Manual | `/proxy` → send `.txt` file |
| Auto-scrape | `/scrapeproxy` — pulls HTTP, SOCKS4, SOCKS5 from 19 GitHub sources, validates live |
| ghostproxies.net | Set `GHOST_KEY` — gateway handles rotation server-side |

Accepted proxy formats:
```
1.2.3.4:8080
1.2.3.4:8080:user:pass
http://user:pass@1.2.3.4:8080
socks4://1.2.3.4:1080
socks5://1.2.3.4:1080
```

---

<div align="center">

Made with 🖤 by **WarXMe**

</div>
