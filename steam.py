import json
import os
import re
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import requests
from bs4 import BeautifulSoup

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
STATE_FILE = "free-steam.json"
LEGACY_STATE_FILE = "free-steam.txt"
CONFIG_FILE = "config.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_config():
    default_config = {
        "secrets": {
            "use_hardcoded_secrets": False,
            "secrets_file": "secrets.json",
        },
        "notifications": {
            "email": True,
            "telegram": True,
            "discord": True,
        }
    }

    if not os.path.exists(CONFIG_FILE):
        return default_config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return default_config

    secrets = data.get("secrets", {})
    notifications = data.get("notifications", {})
    return {
        "secrets": {
            "use_hardcoded_secrets": bool(secrets.get("use_hardcoded_secrets", False)),
            "secrets_file": str(secrets.get("secrets_file", "secrets.json")),
        },
        "notifications": {
            "email": bool(notifications.get("email", True)),
            "telegram": bool(notifications.get("telegram", True)),
            "discord": bool(notifications.get("discord", True)),
        }
    }


CONFIG = load_config()


def load_secrets():
    if CONFIG["secrets"]["use_hardcoded_secrets"]:
        secrets_file = CONFIG["secrets"]["secrets_file"]
        try:
            with open(secrets_file, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            data = {}

        email_data = data.get("email", {})
        telegram_data = data.get("telegram", {})
        discord_data = data.get("discord", {})
        return {
            "EMAIL": str(email_data.get("email", "")),
            "PASSWORD": str(email_data.get("password", "")),
            "TO_EMAIL": str(email_data.get("to_email", "")),
            "TELEGRAM_BOT_TOKEN": str(telegram_data.get("bot_token", "")),
            "TELEGRAM_CHAT_ID": str(telegram_data.get("chat_id", "")),
            "DISCORD_BOT_TOKEN": str(discord_data.get("bot_token", "")),
            "DISCORD_CHANNEL_ID": str(discord_data.get("channel_id", "")),
        }

    return {
        "EMAIL": os.getenv("EMAIL", ""),
        "PASSWORD": os.getenv("PASSWORD", ""),
        "TO_EMAIL": os.getenv("TO_EMAIL", ""),
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
        "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN", ""),
        "DISCORD_CHANNEL_ID": os.getenv("DISCORD_CHANNEL_ID", ""),
    }


SECRETS = load_secrets()
EMAIL = SECRETS["EMAIL"]
PASSWORD = SECRETS["PASSWORD"]
TO_EMAIL = SECRETS["TO_EMAIL"]
TELEGRAM_BOT_TOKEN = SECRETS["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = SECRETS["TELEGRAM_CHAT_ID"]
DISCORD_BOT_TOKEN = SECRETS["DISCORD_BOT_TOKEN"] 
DISCORD_CHANNEL_ID = SECRETS["DISCORD_CHANNEL_ID"] 


def parse_csv_values(value):
    return [item.strip() for item in str(value).split(",") if item.strip()]

def clean_text(value):
    return re.sub(r"\s+", " ", (value or "")).strip()


def is_generic_weekend_title(title):
    return clean_text(title).lower() in {
        "free weekend",
        "play for free",
        "weekend deal",
        "free to play weekend",
    }


def extract_appid_from_url(url):
    match = re.search(r"/app/(\d+)", url or "")
    return match.group(1) if match else None


def fetch_app_name(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=en"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json().get(str(appid), {})
    if data.get("success"):
        return clean_text((data.get("data") or {}).get("name"))
    return ""


def resolve_weekend_title(item):
    for key in ["name", "header", "subheader", "title"]:
        candidate = clean_text(item.get(key))
        if candidate and not is_generic_weekend_title(candidate):
            return candidate

    body = clean_text(item.get("body"))
    patterns = [
        r"Play\s+(.+?)\s+for\s+free",
        r"(.+?)\s+Free Weekend",
        r"Free Weekend[:\-]?\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE)
        if match:
            title = clean_text(match.group(1))
            if title and not is_generic_weekend_title(title):
                return title

    appid = item.get("id") or item.get("appid") or extract_appid_from_url(item.get("url"))
    if appid:
        try:
            app_name = fetch_app_name(appid)
            if app_name:
                return app_name
        except Exception:
            pass

    return clean_text(item.get("name")) or "Unknown Free Weekend Game"


def get_free_to_claim():
    url = "https://store.steampowered.com/search/?maxprice=free&specials=1"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    games = []
    for game in soup.find_all("a", class_="search_result_row"):
        title = game.find("span", class_="title")
        price = game.find("div", class_="discount_final_price")
        discount = game.find("div", class_="discount_pct")
        image = game.find("img")

        if not title:
            continue

        price_text = clean_text(price.text if price else "")
        discount_text = clean_text(discount.text if discount else "")

        if price_text in ["Free", "₹0", "$0.00"] or "100%" in discount_text:
            games.append(
                {
                    "type": "Free to Keep",
                    "title": clean_text(title.text),
                    "link": game.get("href"),
                    "image": image["src"] if image else "",
                    "time": "Limited Time Offer",
                }
            )

    return games


def get_free_weekend():
    url = "https://store.steampowered.com/api/featuredcategories/"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()

    games = []
    for section in data.values():
        if isinstance(section, dict) and "items" in section:
            for item in section["items"]:
                name = clean_text(item.get("name")).lower()
                body = clean_text(item.get("body")).lower()

                if "free weekend" in name or "play for free" in body or "free weekend" in body:
                    games.append(
                        {
                            "type": "Free Weekend",
                            "title": resolve_weekend_title(item),
                            "link": item.get("url"),
                            "image": item.get("header_image", ""),
                            "time": clean_text(item.get("body")) or "Ends Soon (Free Weekend)",
                        }
                    )

    unique_games = []
    seen = set()
    for game in games:
        key = (game["title"].lower(), game.get("link") or "")
        if key not in seen:
            seen.add(key)
            unique_games.append(game)

    return unique_games


def fetch_games():
    games = get_free_to_claim() + get_free_weekend()
    games.sort(key=lambda game: (game["title"].lower(), game["type"].lower()))
    return games


def generate_signature(games):
    return "|".join(
        sorted(f"{game['type']}::{game['title']}::{game.get('link', '')}" for game in games)
    )


def load_saved_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}

    if os.path.exists(LEGACY_STATE_FILE):
        with open(LEGACY_STATE_FILE, "r", encoding="utf-8") as file:
            return {"signature": file.read().strip()}

    return {}


def has_changed(signature):
    return load_saved_state().get("signature") != signature


def save_state(signature, games):
    state = {
        "signature": signature,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "games": games,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def build_html(games):
    cards = ""
    for game in games:
        color = "#22c55e" if game["type"] == "Free to Keep" else "#3b82f6"
        cards += f"""
        <div style="background:#1e293b;border-radius:15px;padding:20px;margin-bottom:25px;">
            <h2 style="color:white;text-align:center;">{game['title']}</h2>
            <img src="{game['image']}" style="width:100%;border-radius:12px;">
            <p style="text-align:center;color:#cbd5f5;margin-top:10px;">
                {game['type']}<br>
                {game['time']}
            </p>
            <div style="text-align:center;margin-top:15px;">
                <a href="{game['link']}"
                   style="display:inline-block;background:{color};
                   color:white;padding:12px 25px;border-radius:8px;
                   text-decoration:none;font-weight:bold;">
                    Open in Steam
                </a>
            </div>
        </div>
        """

    return f"""
    <html>
    <body style="background:#020617;font-family:Arial;padding:20px;">
        <h1 style="color:#22c55e;text-align:center;">Steam Free Games</h1>
        {cards if cards else "<p style='color:white;text-align:center;'>No free games</p>"}
        <p style="color:gray;text-align:center;margin-top:40px;">Auto Steam Notifier</p>
    </body>
    </html>
    """


def send_email(subject, html):
    if not CONFIG["notifications"]["email"]:
        return

    if not EMAIL or not PASSWORD or not TO_EMAIL:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)


def build_telegram_summary(games):
    return f"<b>Steam Free Games Update</b>\n\n<b>Total offers:</b> {len(games)}"


def build_telegram_game_caption(game):
    title = escape(game["title"])
    offer_type = escape(game.get("type", "Offer"))
    time_text = escape(game.get("time", "Limited time"))
    link = escape(game.get("link", "https://store.steampowered.com/"))
    return (
        f"<b>{offer_type}</b>\n"
        f"<a href=\"{link}\">{title}</a>\n"
        f"<b>Details:</b> {time_text}\n"
        f"<a href=\"{link}\">Click here to open the store page</a>"
    )


def send_telegram_text(message):
    if not CONFIG["notifications"]["telegram"]:
        return

    chat_ids = parse_csv_values(TELEGRAM_CHAT_ID)
    if not TELEGRAM_BOT_TOKEN or not chat_ids:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in chat_ids:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": False,
                "parse_mode": "HTML",
            },
            timeout=30,
        )
        response.raise_for_status()


def send_telegram_photo(photo_url, caption):
    if not CONFIG["notifications"]["telegram"]:
        return

    chat_ids = parse_csv_values(TELEGRAM_CHAT_ID)
    if not TELEGRAM_BOT_TOKEN or not chat_ids:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    for chat_id in chat_ids:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption[:1024],
                "parse_mode": "HTML",
            },
            timeout=30,
        )
        response.raise_for_status()


def send_telegram_notifications(games):
    send_telegram_text(build_telegram_summary(games))

    for game in games:
        caption = build_telegram_game_caption(game)
        if game.get("image"):
            send_telegram_photo(game["image"], caption)
        else:
            send_telegram_text(caption)


# ── Discord ──────────────────────────────────────────────────────────────────

DISCORD_API = "https://discord.com/api/v10/channels/{channel_id}/messages"


def _discord_post(payload):
    """POST one message to the configured Discord channel."""
    channel_ids = parse_csv_values(DISCORD_CHANNEL_ID)
    if not DISCORD_BOT_TOKEN or not channel_ids:
        return
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    for channel_id in channel_ids:
        url = DISCORD_API.format(channel_id=channel_id)
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()


def build_discord_game_embed(game):
    offer_type = game.get("type", "Offer")
    colour = 0x22C55E if offer_type == "Free to Keep" else 0x3B82F6
    embed = {
        "title": game["title"],
        "url": game.get("link", "https://store.steampowered.com/"),
        "color": colour,
        "fields": [
            {"name": "Type",    "value": offer_type,                  "inline": True},
            {"name": "Details", "value": game.get("time", "N/A"),     "inline": True},
        ],
        "footer": {"text": "Steam Free Games Notifier"},
    }
    if game.get("image"):
        embed["image"] = {"url": game["image"]}
    return embed


def send_discord_notifications(games):
    if not CONFIG["notifications"]["discord"]:
        return

    if not DISCORD_BOT_TOKEN or not DISCORD_CHANNEL_ID:
        return

    # Summary message
    _discord_post({"content": f"🎮 **Steam Free Games Update**\n📦 **Total offers:** {len(games)}"})

    # One embed per game
    for game in games:
        _discord_post({"embeds": [build_discord_game_embed(game)]})


if __name__ == "__main__":
    games = fetch_games()
    signature = generate_signature(games)

    if not has_changed(signature):
        print("No Steam changes.")
    else:
        print("New Steam update detected.")
        subject = "Steam Free Games Update"
        html = build_html(games)
        send_email(subject, html)
        send_telegram_notifications(games)
        send_discord_notifications(games)
        save_state(signature, games)
        print("Notifications sent and JSON state saved.")
