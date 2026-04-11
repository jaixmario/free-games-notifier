import json
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import requests

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
API_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US"
STATE_FILE = "free.json"
LEGACY_STATE_FILE = "free.txt"
CONFIG_FILE = "config.json"


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


def format_date_ist(date_str):
    try:
        utc_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        ist_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))
        return ist_time.strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return "N/A"


def normalize_store_path(value):
    if not value:
        return ""

    value = str(value).strip().strip("/")
    if not value:
        return ""

    parts = [part for part in value.split("/") if part and part.lower() not in {"home", "browse"}]
    if not parts:
        return ""

    if parts[0].lower() == "p" and len(parts) > 1:
        return f"p/{parts[1]}"

    if len(parts) == 1:
        return f"p/{parts[0]}"

    return "/".join(parts)


def build_store_link(game):
    candidate_paths = []

    for mapping in game.get("offerMappings", []) or []:
        candidate_paths.append(mapping.get("pageSlug"))

    catalog_ns = game.get("catalogNs") or {}
    for mapping in catalog_ns.get("mappings", []) or []:
        candidate_paths.append(mapping.get("pageSlug"))

    candidate_paths.extend(
        [
            game.get("productSlug"),
            game.get("urlSlug"),
            game.get("offerType"),
        ]
    )

    for candidate in candidate_paths:
        normalized = normalize_store_path(candidate)
        if normalized:
            return f"https://store.epicgames.com/en-US/{normalized}"

    return "https://store.epicgames.com/en-US/"


def fetch_games():
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    current_games = []
    upcoming_games = []
    elements = data["data"]["Catalog"]["searchStore"]["elements"]

    for game in elements:
        try:
            title = game["title"]
            image = ""

            for img in game.get("keyImages", []):
                if img["type"] in ["OfferImageWide", "DieselStoreFrontWide"]:
                    image = img["url"]
                    break

            link = build_store_link(game)
            promotions = game.get("promotions") or {}

            if promotions.get("promotionalOffers"):
                for offer in promotions["promotionalOffers"][0]["promotionalOffers"]:
                    if offer["discountSetting"]["discountPercentage"] == 0:
                        current_games.append(
                            {
                                "title": title,
                                "image": image,
                                "link": link,
                                "start": format_date_ist(offer.get("startDate")),
                                "end": format_date_ist(offer.get("endDate")),
                            }
                        )

            if promotions.get("upcomingPromotionalOffers"):
                for offer in promotions["upcomingPromotionalOffers"][0]["promotionalOffers"]:
                    if offer["discountSetting"]["discountPercentage"] == 0:
                        upcoming_games.append(
                            {
                                "title": title,
                                "image": image,
                                "link": link,
                                "start": format_date_ist(offer.get("startDate")),
                                "end": format_date_ist(offer.get("endDate")),
                            }
                        )
        except Exception:
            continue

    current_games.sort(key=lambda game: game["title"].lower())
    upcoming_games.sort(key=lambda game: game["title"].lower())
    return current_games, upcoming_games


def generate_signature(current_games, upcoming_games):
    current_titles = sorted(game["title"] for game in current_games)
    upcoming_titles = sorted(game["title"] for game in upcoming_games)
    return "CURRENT:" + ",".join(current_titles) + "|UPCOMING:" + ",".join(upcoming_titles)


def load_saved_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    if os.path.exists(LEGACY_STATE_FILE):
        with open(LEGACY_STATE_FILE, "r", encoding="utf-8") as file:
            return {"signature": file.read().strip()}

    return {}


def has_changed(signature):
    return load_saved_state().get("signature") != signature


def save_state(signature, current_games, upcoming_games):
    state = {
        "signature": signature,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "current_games": current_games,
        "upcoming_games": upcoming_games,
    }

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def build_html(current_games, upcoming_games):
    def current_cards(games):
        cards = ""
        for game in games:
            cards += f"""
            <div style="background:#1e293b;border-radius:15px;padding:20px;margin-bottom:25px;">
                <h2 style="color:white;text-align:center;">{game['title']}</h2>
                <img src="{game['image']}" style="width:100%;border-radius:12px;">
                <p style="color:#cbd5f5;text-align:center;margin-top:10px;">
                    <b>Start:</b> {game['start']}<br>
                    <b>Ends:</b> {game['end']}
                </p>
                <div style="text-align:center;margin-top:15px;">
                    <a href="{game['link']}"
                       style="display:inline-block;background:#22c55e;color:white;
                       padding:12px 25px;border-radius:8px;text-decoration:none;font-weight:bold;">
                        Claim Now
                    </a>
                </div>
            </div>
            """
        return cards

    def upcoming_cards(games):
        cards = ""
        for game in games:
            cards += f"""
            <div style="background:#1e293b;border-radius:15px;padding:20px;margin-bottom:25px;">
                <h2 style="color:white;text-align:center;">{game['title']}</h2>
                <img src="{game['image']}" style="width:100%;border-radius:12px;">
                <p style="color:#cbd5f5;text-align:center;margin-top:10px;">
                    <b>Starts:</b> {game['start']}<br>
                    <b>Ends:</b> {game['end']}
                </p>
            </div>
            """
        return cards

    return f"""
    <html>
    <body style="background:#020617;font-family:Arial;padding:20px;">
        <h1 style="color:#22c55e;text-align:center;">Epic Free Games Right Now</h1>
        {current_cards(current_games) if current_games else "<p style='color:white;text-align:center;'>No current games</p>"}
        <hr style="margin:40px 0;border-color:#334155;">
        <h1 style="color:#facc15;text-align:center;">Upcoming Free Games</h1>
        {upcoming_cards(upcoming_games) if upcoming_games else "<p style='color:white;text-align:center;'>No upcoming games revealed</p>"}
        <p style="color:gray;text-align:center;margin-top:40px;">Auto Epic Games Notifier</p>
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


def build_telegram_summary(current_games, upcoming_games):
    summary = ["<b>Epic Free Games Update</b>", ""]
    summary.append(f"<b>Free now:</b> {len(current_games)}")
    summary.append(f"<b>Upcoming:</b> {len(upcoming_games)}")
    return "\n".join(summary)


def build_telegram_game_caption(game, label):
    title = escape(game["title"])
    link = escape(game["link"])
    start = escape(game.get("start", "N/A"))
    end = escape(game.get("end", "N/A"))
    return (
        f"<b>{escape(label)}</b>\n"
        f"<a href=\"{link}\">{title}</a>\n"
        f"<b>Start:</b> {start}\n"
        f"<b>End:</b> {end}\n"
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


def send_telegram_notifications(current_games, upcoming_games):
    send_telegram_text(build_telegram_summary(current_games, upcoming_games))

    for game in current_games:
        caption = build_telegram_game_caption(game, "Epic Free Now")
        if game.get("image"):
            send_telegram_photo(game["image"], caption)
        else:
            send_telegram_text(caption)

    for game in upcoming_games:
        caption = build_telegram_game_caption(game, "Epic Upcoming")
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


def build_discord_game_embed(game, label, colour):
    embed = {
        "title": game["title"],
        "url": game["link"],
        "color": colour,
        "fields": [
            {"name": "Start", "value": game.get("start", "N/A"), "inline": True},
            {"name": "End",   "value": game.get("end", "N/A"),   "inline": True},
        ],
        "footer": {"text": label},
    }
    if game.get("image"):
        embed["image"] = {"url": game["image"]}
    return embed


def send_discord_notifications(current_games, upcoming_games):
    if not CONFIG["notifications"]["discord"]:
        return

    if not DISCORD_BOT_TOKEN or not DISCORD_CHANNEL_ID:
        return

    # Summary message
    summary_lines = [
        "**🎮 Epic Free Games Update**",
        f"🟢 **Free now:** {len(current_games)}",
        f"🟡 **Upcoming:** {len(upcoming_games)}",
    ]
    _discord_post({"content": "\n".join(summary_lines)})

    # One embed per current game  (colour: green 0x22c55e)
    for game in current_games:
        embed = build_discord_game_embed(game, "\ud83d\udfe2 Epic Free Now", 0x22C55E)
        _discord_post({"embeds": [embed]})

    # One embed per upcoming game  (colour: yellow 0xfacc15)
    for game in upcoming_games:
        embed = build_discord_game_embed(game, "\ud83d\udfe1 Epic Upcoming", 0xFACC15)
        _discord_post({"embeds": [embed]})


if __name__ == "__main__":
    current_games, upcoming_games = fetch_games()
    signature = generate_signature(current_games, upcoming_games)

    if not has_changed(signature):
        print("No changes. Email not sent.")
    else:
        print("New Epic update detected. Sending notifications...")
        current_titles = ", ".join(game["title"] for game in current_games) or "None"
        upcoming_titles = ", ".join(game["title"] for game in upcoming_games) or "TBA"
        subject = f"Free Now: {current_titles} | Next: {upcoming_titles}"
        html = build_html(current_games, upcoming_games)
        send_email(subject, html)
        send_telegram_notifications(current_games, upcoming_games)
        send_discord_notifications(current_games, upcoming_games)
        save_state(signature, current_games, upcoming_games)
        print("Notifications sent and JSON state saved.")
