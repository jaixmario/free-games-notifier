import json
import os
import re
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_FILE = "free-steam.json"
LEGACY_STATE_FILE = "free-steam.txt"
CONFIG_FILE = "config.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_config():
    default_config = {
        "notifications": {
            "email": True,
            "telegram": True,
        }
    }

    if not os.path.exists(CONFIG_FILE):
        return default_config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return default_config

    notifications = data.get("notifications", {})
    return {
        "notifications": {
            "email": bool(notifications.get("email", True)),
            "telegram": bool(notifications.get("telegram", True)),
        }
    }


CONFIG = load_config()
 

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


def build_telegram_message(games):
    lines = ["Steam Free Games Update", ""]

    if not games:
        lines.append("No Steam offers found.")
        return "\n".join(lines)

    for game in games:
        lines.append(f"- {game['title']} ({game['type']})")
        if game.get("time"):
            lines.append(f"  {game['time']}")
        if game.get("link"):
            lines.append(f"  {game['link']}")

    return "\n".join(lines)


def send_telegram_message(message):
    if not CONFIG["notifications"]["telegram"]:
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    response.raise_for_status()


if __name__ == "__main__":
    games = fetch_games()
    signature = generate_signature(games)

    if not has_changed(signature):
        print("No Steam changes.")
    else:
        print("New Steam update detected.")
        subject = "Steam Free Games Update"
        html = build_html(games)
        telegram_message = build_telegram_message(games)
        send_email(subject, html)
        send_telegram_message(telegram_message)
        save_state(signature, games)
        print("Notifications sent and JSON state saved.")
