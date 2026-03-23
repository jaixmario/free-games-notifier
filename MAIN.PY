import requests
import smtplib
import os
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= CONFIG =================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
API_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US"
STATE_FILE = "free.txt"
# ==========================================


# 🇮🇳 Convert UTC → IST
def format_date_ist(date_str):
    try:
        utc_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        ist_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))
        return ist_time.strftime("%d %b %Y, %I:%M %p IST")
    except:
        return "N/A"


# 📦 Fetch games from API
def fetch_games():
    res = requests.get(API_URL)
    data = res.json()

    current_games = []
    upcoming_games = []

    elements = data['data']['Catalog']['searchStore']['elements']

    for game in elements:
        try:
            title = game["title"]

            # Image
            image = ""
            for img in game.get("keyImages", []):
                if img["type"] in ["OfferImageWide", "DieselStoreFrontWide"]:
                    image = img["url"]

            # Link
            slug = game.get("productSlug") or game.get("urlSlug")
            link = f"https://store.epicgames.com/en-US/p/{slug}"

            promotions = game.get("promotions")

            if promotions:
                # CURRENT FREE
                if promotions.get("promotionalOffers"):
                    for offer in promotions["promotionalOffers"][0]["promotionalOffers"]:
                        if offer["discountSetting"]["discountPercentage"] == 0:
                            current_games.append({
                                "title": title,
                                "image": image,
                                "link": link,
                                "start": format_date_ist(offer.get("startDate")),
                                "end": format_date_ist(offer.get("endDate"))
                            })

                # UPCOMING FREE
                if promotions.get("upcomingPromotionalOffers"):
                    for offer in promotions["upcomingPromotionalOffers"][0]["promotionalOffers"]:
                        if offer["discountSetting"]["discountPercentage"] == 0:
                            upcoming_games.append({
                                "title": title,
                                "image": image,
                                "link": link,
                                "start": format_date_ist(offer.get("startDate")),
                                "end": format_date_ist(offer.get("endDate"))
                            })

        except Exception:
            continue

    return current_games, upcoming_games


# 🧠 Generate signature for change detection
def generate_signature(current_games, upcoming_games):
    current_titles = sorted([g["title"] for g in current_games])
    upcoming_titles = sorted([g["title"] for g in upcoming_games])

    return "CURRENT:" + ",".join(current_titles) + "|UPCOMING:" + ",".join(upcoming_titles)


def has_changed(signature):
    if not os.path.exists(STATE_FILE):
        return True

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        old = f.read().strip()

    return old != signature


def save_signature(signature):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(signature)


# 🎨 Build HTML Email
def build_html(current_games, upcoming_games):

    def current_cards(games):
        cards = ""
        for g in games:
            cards += f"""
            <div style="background:#1e293b;border-radius:15px;padding:20px;margin-bottom:25px;">
                <h2 style="color:white;text-align:center;">{g['title']}</h2>
                
                <img src="{g['image']}" style="width:100%;border-radius:12px;">
                
                <p style="color:#cbd5f5;text-align:center;margin-top:10px;">
                    📅 <b>Start:</b> {g['start']}<br>
                    ⏳ <b>Ends:</b> {g['end']}
                </p>

                <div style="text-align:center;margin-top:15px;">
                    <a href="{g['link']}" 
                       style="display:inline-block;background:#22c55e;color:white;
                       padding:12px 25px;border-radius:8px;text-decoration:none;font-weight:bold;">
                        🎮 Claim Now
                    </a>
                </div>
            </div>
            """
        return cards

    def upcoming_cards(games):
        cards = ""
        for g in games:
            cards += f"""
            <div style="background:#1e293b;border-radius:15px;padding:20px;margin-bottom:25px;">
                <h2 style="color:white;text-align:center;">{g['title']}</h2>
                
                <img src="{g['image']}" style="width:100%;border-radius:12px;">
                
                <p style="color:#cbd5f5;text-align:center;margin-top:10px;">
                    📅 <b>Starts:</b> {g['start']}<br>
                    ⏳ <b>Ends:</b> {g['end']}
                </p>
            </div>
            """
        return cards

    html = f"""
    <html>
    <body style="background:#020617;font-family:Arial;padding:20px;">
        
        <h1 style="color:#22c55e;text-align:center;">🎮 Free Games Right Now</h1>
        {current_cards(current_games) if current_games else "<p style='color:white;text-align:center;'>No current games</p>"}

        <hr style="margin:40px 0;border-color:#334155;">

        <h1 style="color:#facc15;text-align:center;">⏳ Upcoming Free Games</h1>
        {upcoming_cards(upcoming_games) if upcoming_games else "<p style='color:white;text-align:center;'>No upcoming games revealed</p>"}

        <p style="color:gray;text-align:center;margin-top:40px;">
            Auto Epic Games Notifier 🇮🇳
        </p>
    </body>
    </html>
    """

    return html


# 📩 Send Email
def send_email(subject, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = TO_EMAIL

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)


# 🚀 MAIN
if __name__ == "__main__":
    current_games, upcoming_games = fetch_games()

    signature = generate_signature(current_games, upcoming_games)

    if not has_changed(signature):
        print("⏸ No changes. Email not sent.")
    else:
        print("🚀 New update detected! Sending email...")

        current_titles = ", ".join([g["title"] for g in current_games]) or "None"
        upcoming_titles = ", ".join([g["title"] for g in upcoming_games]) or "TBA"

        subject = f"🔥 Free Now: {current_titles} | Next: {upcoming_titles}"
        html = build_html(current_games, upcoming_games)

        send_email(subject, html)

        save_signature(signature)

        print("✅ Email sent & state saved.")