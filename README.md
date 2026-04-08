# Free Games Auto Notifier

> Automatically tracks **Epic Games** and **Steam** free game offers and sends you a beautiful HTML email notification whenever new free games appear — powered by GitHub Actions.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-success?logo=github-actions&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Schedule](https://img.shields.io/badge/Runs%20Every-6%20Hours-orange?logo=clockify&logoColor=white)

<!-- README_AUTO_SECTION:START -->
## Free Games Right Now

Last updated: **08 Apr 2026, 08:11 PM IST**  
Source: Epic fallback from saved state, Steam live data

### Epic Games
- **Clone Drone in the Danger Zone** - free until `09 Apr 2026, 08:30 PM IST` ([Claim](https://store.epicgames.com/en-US/p/clone-drone-in-the-danger-zone-4daf6e))
- **TOMAK: Save the Earth Regeneration** - free until `16 Apr 2026, 08:30 PM IST` ([Claim](https://store.epicgames.com/en-US/p/tomak-save-the-earth-regeneration-c1207c))

### Upcoming on Epic
- **Prop Sumo** - starts `09 Apr 2026, 08:30 PM IST` ([Store page](https://store.epicgames.com/en-US/p/propsumo-ca8bd7))

### Steam
- **Chamber Survival** - Free to Keep ([Open](https://store.steampowered.com/app/2943780/Chamber_Survival/?snr=1_7_7_2300_150_1))
<!-- README_AUTO_SECTION:END -->

---

## Features

- Epic Games support for current and upcoming free promotions
- Steam support for free-to-keep deals and free weekend events
- HTML email and Telegram notifications
- Change detection to avoid duplicate emails
- Automatic README refresh on every scheduled workflow run
- GitHub Actions automation every 6 hours

---

## Project Structure

```text
free-games-notifier/
|-- epic.PY
|-- steam.py
|-- generate_readme.py
|-- config.json
|-- free.txt
|-- free-steam.txt
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
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Telegram user, group, or channel chat id |
| `TO_EMAIL` | Recipient email address |

Use a Gmail App Password, not your normal account password. Telegram is optional, but if you set both Telegram secrets the workflow will send bot messages too.

### 4. Control notification types with `config.json`

```json
{
  "notifications": {
    "email": true,
    "telegram": false
  }
}
```

If a notification type is set to `false`, the scripts will skip it completely and will not require those credentials to be present.

---

## How It Works

### `epic.PY`

1. Calls the Epic Games promotions API.
2. Extracts current and upcoming free games.
3. Formats dates in IST.
4. Compares the latest titles with `free.txt`.
5. Sends email and optional Telegram alerts only when the lineup changes.

### `steam.py`

1. Scrapes Steam search results for discounted free offers.
2. Checks Steam featured categories for free weekend events.
3. Compares the latest titles with `free-steam.txt`.
4. Sends email and optional Telegram alerts only when the lineup changes.

### `generate_readme.py`

1. Fetches the latest Epic and Steam game data.
2. Rebuilds the auto-managed section at the top of this README.
3. Falls back to saved state files if a live fetch fails.

---

## GitHub Actions Workflow

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

```powershell
$env:EMAIL="you@gmail.com"
$env:PASSWORD="your-app-password"
$env:TELEGRAM_BOT_TOKEN="123456:telegram-bot-token"
$env:TELEGRAM_CHAT_ID="123456789"
$env:TO_EMAIL="recipient@example.com"

python epic.PY
python steam.py
python generate_readme.py
```

---

## Security Notes

- Credentials are never committed to the repository.
- Secrets are injected at runtime through GitHub Actions.
- State files only store game-title signatures.

---

## License

This project is open source and available under the [MIT License](LICENSE).