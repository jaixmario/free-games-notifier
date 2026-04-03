import requests
import smtplib
import os
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= CONFIG =================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
STATE_FILE = "free-steam.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
# ==========================================


# -----------------------------
# 1. FREE TO KEEP (SCRAPE)
# -----------------------------
def get_free_to_claim():
    URL = "https://store.steampowered.com/search/?maxprice=free&specials=1"
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    games = []

    results = soup.find_all("a", class_="search_result_row")

    for game in results:
        title = game.find("span", class_="title")
        price = game.find("div", class_="discount_final_price")
        discount = game.find("div", class_="discount_pct")
        image = game.find("img")

        if title:
            price_text = price.text.strip() if price else ""
            discount_text = discount.text.strip() if discount else ""

            if price_text in ["Free", "₹0"] or "100%" in discount_text:
                games.append({
                    "type": "Free to Keep",
                    "title": title.text.strip(),
                    "link": game.get("href"),
                    "image": image["src"] if image else "",
                    "time": "⏳ Limited Time Offer"
                })

    return games


# -----------------------------
# 2. FREE WEEKEND (API)
# -----------------------------
def get_free_weekend():
    url = "https://store.steampowered.com/api/featuredcategories/"
    res = requests.get(url, headers=HEADERS)
    data = res.json()

    games = []

    for key in data:
        section = data[key]

        if isinstance(section, dict) and "items" in section:
            for item in section["items"]:
                name = item.get("name", "").lower()
                body = item.get("body", "").lower()

                if "free weekend" in name or "play for free" in body:
                    games.append({
                        "type": "Free Weekend",
                        "title": item.get("name"),
                        "link": item.get("url"),
                        "image": item.get("header_image", ""),
                        "time": "⏳ Ends Soon (Free Weekend)"
                    })

    return games


# -----------------------------
# FETCH
# -----------------------------
def fetch_games():
    return get_free_to_claim() + get_free_weekend()


# -----------------------------
# CHANGE DETECTION
# -----------------------------
def generate_signature(games):
    return ",".join(sorted([g["title"] for g in games]))


def has_changed(sig):
    if not os.path.exists(STATE_FILE):
        return True

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() != sig


def save_signature(sig):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(sig)


# -----------------------------
# HTML UI
# -----------------------------
def build_html(games):
    cards = ""

    for g in games:
        color = "#22c55e" if g["type"] == "Free to Keep" else "#3b82f6"

        cards += f"""
        <div style="background:#1e293b;border-radius:15px;padding:20px;margin-bottom:25px;">
            
            <h2 style="color:white;text-align:center;">{g['title']}</h2>

            <img src="{g['image']}" style="width:100%;border-radius:12px;">

            <p style="text-align:center;color:#cbd5f5;margin-top:10px;">
                🎯 {g['type']}<br>
                {g['time']}
            </p>

            <div style="text-align:center;margin-top:15px;">
                <a href="{g['link']}" 
                   style="display:inline-block;background:{color};
                   color:white;padding:12px 25px;border-radius:8px;
                   text-decoration:none;font-weight:bold;">
                    🎮 Open in Steam
                </a>
            </div>

        </div>
        """

    html = f"""
    <html>
    <body style="background:#020617;font-family:Arial;padding:20px;">
        
        <h1 style="color:#22c55e;text-align:center;">
            🎮 Steam Free Games
        </h1>

        {cards if cards else "<p style='color:white;text-align:center;'>No free games</p>"}

        <p style="color:gray;text-align:center;margin-top:40px;">
            Auto Steam Notifier ⚡
        </p>

    </body>
    </html>
    """

    return html


# -----------------------------
# EMAIL
# -----------------------------
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


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    games = fetch_games()
    sig = generate_signature(games)

    if not has_changed(sig):
        print("⏸ No changes")
    else:
        print("🚀 New update!")

        subject = "🔥 Steam Free Games Update"
        html = build_html(games)

        send_email(subject, html)
        save_signature(sig)

        print("✅ Email sent")