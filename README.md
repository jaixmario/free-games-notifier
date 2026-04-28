# Free Games Auto Notifier

> Automatically tracks **Epic Games** and **Steam** free game offers and sends you a beautiful HTML email notification whenever new free games appear — powered by GitHub Actions.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-success?logo=github-actions&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Schedule](https://img.shields.io/badge/Runs%20Every-6%20Hours-orange?logo=clockify&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?logo=discord&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud%20API-25D366?logo=whatsapp&logoColor=white)

<!-- README_AUTO_SECTION:START -->
## Free Games Right Now

Last updated: **28 Apr 2026, 06:29 PM IST**  
Source: Epic fallback from saved state, Steam live data

### Epic Games
- **DOOMBLADE** - free until `30 Apr 2026, 08:30 PM IST` ([Claim](https://store.epicgames.com/en-US/p/doomblade-afdf9a))

### Upcoming on Epic
- **Firestone Online Idle RPG** - starts `30 Apr 2026, 08:30 PM IST` ([Store page](https://store.epicgames.com/en-US/p/firestone-online-idle-rpg-bfd04b))
- **Oddsparks: An Automation Adventure** - starts `30 Apr 2026, 08:30 PM IST` ([Store page](https://store.epicgames.com/en-US/p/oddsparks-58440c))

### Steam
- **Aeonic** - Free to Keep ([Open](https://store.steampowered.com/app/3277530/Aeonic/?snr=1_7_7_2300_150_1))
- **Cthulhu: The Cosmic Abyss - Sanity Skin Pack** - Free to Keep ([Open](https://store.steampowered.com/app/4277070/Cthulhu_The_Cosmic_Abyss__Sanity_Skin_Pack/?snr=1_7_7_2300_150_1))
<!-- README_AUTO_SECTION:END -->

---

## Features

- Epic Games support for current and upcoming free promotions
- Steam support for free-to-keep deals and free weekend events
- HTML email notifications
- Telegram bot notifications with per-game photo cards
- **Discord bot notifications with rich embeds** (title, image, dates, store link)
- **WhatsApp Cloud API notifications** with summary and per-game text messages
- Change detection to avoid duplicate notifications
- Automatic README refresh on every scheduled workflow run
- GitHub Actions automation every 6 hours

---

## Project Structure

```text
free-games-notifier/
|-- epic.PY
|-- steam.py
|-- start.py
|-- generate_readme.py
|-- config.json
|-- secrets.json
|-- free.json
|-- free-steam.json
|-- index.html
|-- SITE/
|   |-- docs.html
|   |-- site.css
|   `-- site.js
`-- .github/
    `-- workflows/
        `-- main.yml
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/free-games-notifier.git
cd free-games-notifier
```

### 2. Install dependencies

```bash
pip install requests beautifulsoup4
```

### 3. Add GitHub secrets

Create these repository secrets in `Settings -> Secrets and variables -> Actions`:

| Secret Name | Description |
|-------------|-------------|
| `EMAIL` | Sender Gmail address |
| `PASSWORD` | Gmail App Password |
| `TO_EMAIL` | Recipient email address or comma-separated email addresses |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Telegram chat ID or comma-separated chat IDs |
| `DISCORD_BOT_TOKEN` | Discord bot token from the Developer Portal |
| `DISCORD_CHANNEL_ID` | Discord channel ID or comma-separated channel IDs |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp Cloud API bearer token |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Cloud API phone number ID |
| `WHATSAPP_TO` | Recipient number or comma-separated numbers in international format |
| `WHATSAPP_API_VERSION` | Optional Graph API version such as `v25.0` |

Use a Gmail App Password, not your normal account password. Each notification type is independent — you can enable only the ones you need via `config.json`.

### 4. Control notification types with `config.json`

```json
{
  "secrets": {
    "use_hardcoded_secrets": false,
    "secrets_file": "secrets.json"
  },
  "notifications": {
    "email": true,
    "telegram": true,
    "discord": true,
    "whatsapp": false
  }
}
```

Set any value to `false` to skip that channel entirely — no credentials required for disabled channels.

### 5. Optional JSON secrets file

Set this in `config.json`:

```json
{
  "secrets": {
    "use_hardcoded_secrets": true,
    "secrets_file": "secrets.json"
  }
}
```

Then fill `secrets.json` with your local values:

```json
{
  "email": {
    "email": "you@gmail.com",
    "password": "your-app-password",
    "to_email": "first@example.com,second@example.com"
  },
  "telegram": {
    "bot_token": "123456:telegram-bot-token",
    "chat_id": "123456789"
  },
  "discord": {
    "bot_token": "YOUR_DISCORD_BOT_TOKEN",
    "channel_id": "YOUR_CHANNEL_ID"
  },
  "whatsapp": {
    "access_token": "EAAG...",
    "phone_number_id": "1126873913833051",
    "to": "919989148967",
    "api_version": "v25.0"
  }
}
```

Email, Telegram, Discord, and WhatsApp all support multiple targets separated by commas. Email delivery is capped at 30 recipients per run.

---

## How It Works

### `epic.PY`

1. Calls the Epic Games promotions API.
2. Extracts current and upcoming free games.
3. Formats dates in IST.
4. Compares the latest JSON snapshot with `free.json`.
5. Sends email, Telegram, Discord, and/or WhatsApp alerts only when the lineup changes.

### `steam.py`

1. Scrapes Steam search results for discounted free offers.
2. Checks Steam featured categories for free weekend events.
3. Compares the latest JSON snapshot with `free-steam.json`.
4. Sends email, Telegram, Discord, and/or WhatsApp alerts only when the lineup changes.

#### Discord notifications

Both scripts post to Discord via the REST API (`POST /channels/{id}/messages`) using a bot token. Each run sends:

- A **summary message** with the total count of free games.
- One **rich embed per game** containing the title (linked to the store page), cover image, and relevant dates or offer type — colour-coded by category.

#### Telegram notifications

Both scripts send Telegram updates using the Bot API. Each run sends:

- A short **summary message**.
- One **formatted message or photo card per game** with clickable links.
- Delivery to one or many chats when `chat_id` contains comma-separated values.

#### WhatsApp notifications

Both scripts send WhatsApp updates through the Meta Cloud API. Each run sends:

- A short **summary message**.
- One **image message with caption and store link** when artwork is available, or a text fallback when it is not.
- Delivery to one or many recipients when `WHATSAPP_TO` contains comma-separated values.

Free-form text messages work inside WhatsApp's customer service window. For messages outside that window, Meta requires approved templates.
GitHub Actions may have WhatsApp API requests blocked or fail unpredictably in some environments, so WhatsApp notifications are best run locally or from a VPS.

### `generate_readme.py`

1. Fetches the latest Epic and Steam game data.
2. Rebuilds the auto-managed section at the top of this README.
3. Falls back to saved state files if a live fetch fails.

---

## GitHub Actions Workflow

Note: GitHub Actions is fine for scraping and README refreshes, but WhatsApp API delivery may be blocked there. Use WhatsApp notifications locally or on a VPS for more reliable sending.

The workflow runs on:

- Schedule: every 6 hours with `0 */6 * * *`
- Manual trigger: `workflow_dispatch`

Each run:

1. Installs dependencies.
2. Runs `epic.PY`.
3. Runs `steam.py`.
4. Runs `generate_readme.py`.
5. Commits updated state files and `README.md` if anything changed.

---

## Run Manually

Run both notifier scripts with one command:

```powershell
python start.py
```

If you want to run with custom environment variables locally:

```powershell
$env:EMAIL="you@gmail.com"
$env:PASSWORD="your-app-password"
$env:TO_EMAIL="first@example.com,second@example.com"
$env:TELEGRAM_BOT_TOKEN="123456:telegram-bot-token"
$env:TELEGRAM_CHAT_ID="123456789"
$env:DISCORD_BOT_TOKEN="your-discord-bot-token"
$env:DISCORD_CHANNEL_ID="your-channel-id"
$env:WHATSAPP_ACCESS_TOKEN="EAAG..."
$env:WHATSAPP_PHONE_NUMBER_ID="123456789"
$env:WHATSAPP_TO="919999999999"
$env:WHATSAPP_API_VERSION="v25.0"

python start.py
python generate_readme.py
```

---

## Security Notes

- Credentials are never committed to the repository.
- Secrets are injected at runtime through GitHub Actions.
- State files are JSON snapshots containing signatures plus game metadata like title, link, image, dates, and offer type.

---

## License

This project is open source and available under the [MIT License](LICENSE).
