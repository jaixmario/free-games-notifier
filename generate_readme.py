import importlib.util
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


sys.dont_write_bytecode = True


README_PATH = Path("README.md")
EPIC_STATE_PATH = Path("free.json")
STEAM_STATE_PATH = Path("free-steam.json")
LEGACY_EPIC_STATE_PATH = Path("free.txt")
LEGACY_STEAM_STATE_PATH = Path("free-steam.txt")
START_MARKER = "<!-- README_AUTO_SECTION:START -->"
END_MARKER = "<!-- README_AUTO_SECTION:END -->"
IST = timezone(timedelta(hours=5, minutes=30))


def load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def parse_epic_state():
    if EPIC_STATE_PATH.exists():
        data = json.loads(EPIC_STATE_PATH.read_text(encoding="utf-8"))
        return data.get("current_games", []), data.get("upcoming_games", [])

    if LEGACY_EPIC_STATE_PATH.exists():
        content = LEGACY_EPIC_STATE_PATH.read_text(encoding="utf-8").strip()
        current_part = ""
        upcoming_part = ""

        if "|UPCOMING:" in content:
            current_part, upcoming_part = content.split("|UPCOMING:", 1)
        else:
            current_part = content

        current_titles = current_part.replace("CURRENT:", "", 1).strip()
        upcoming_titles = upcoming_part.strip()
        current_games = [{"title": title.strip()} for title in current_titles.split(",") if title.strip()]
        upcoming_games = [{"title": title.strip()} for title in upcoming_titles.split(",") if title.strip()]
        return current_games, upcoming_games

    return [], []


def parse_steam_state():
    if STEAM_STATE_PATH.exists():
        data = json.loads(STEAM_STATE_PATH.read_text(encoding="utf-8"))
        return data.get("games", [])

    if LEGACY_STEAM_STATE_PATH.exists():
        content = LEGACY_STEAM_STATE_PATH.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return [{"title": title.strip(), "type": "Tracked offer"} for title in content.split(",") if title.strip()]

    return []


def fetch_epic_games():
    try:
        epic_module = load_module("epic_module", str(Path("epic.PY").resolve()))
        current_games, upcoming_games = epic_module.fetch_games()
        return current_games, upcoming_games, True
    except Exception:
        current_games, upcoming_games = parse_epic_state()
        return current_games, upcoming_games, False


def fetch_steam_games():
    try:
        steam_module = load_module("steam_module", str(Path("steam.py").resolve()))
        games = steam_module.fetch_games()
        return games, True
    except Exception:
        games = parse_steam_state()
        return games, False


def render_epic_games(games):
    if not games:
        return "- No Epic Games freebies found."

    lines = []
    for game in games:
        title = game.get("title", "Unknown title")
        end_date = game.get("end")
        link = game.get("link")
        if link and end_date:
            lines.append(f"- **{title}** - free until `{end_date}` ([Claim]({link}))")
        elif link:
            lines.append(f"- **{title}** ([Claim]({link}))")
        else:
            lines.append(f"- **{title}**")
    return "\n".join(lines)


def render_upcoming_epic_games(games):
    if not games:
        return "- No upcoming Epic Games reveals right now."

    lines = []
    for game in games:
        title = game.get("title", "Unknown title")
        start_date = game.get("start")
        link = game.get("link")
        if link and start_date:
            lines.append(f"- **{title}** - starts `{start_date}` ([Store page]({link}))")
        elif start_date:
            lines.append(f"- **{title}** - starts `{start_date}`")
        else:
            lines.append(f"- **{title}**")
    return "\n".join(lines)


def render_steam_games(games):
    if not games:
        return "- No Steam freebies found."

    lines = []
    for game in games:
        title = game.get("title", "Unknown title")
        offer_type = game.get("type")
        link = game.get("link")
        if link and offer_type:
            lines.append(f"- **{title}** - {offer_type} ([Open]({link}))")
        elif offer_type:
            lines.append(f"- **{title}** - {offer_type}")
        else:
            lines.append(f"- **{title}**")
    return "\n".join(lines)


def build_auto_section():
    current_games, upcoming_games, epic_live = fetch_epic_games()
    steam_games, steam_live = fetch_steam_games()
    updated_at = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")

    source_note = ", ".join(
        [
            "Epic live data" if epic_live else "Epic fallback from saved state",
            "Steam live data" if steam_live else "Steam fallback from saved state",
        ]
    )

    return "\n".join(
        [
            START_MARKER,
            "## Free Games Right Now",
            "",
            f"Last updated: **{updated_at}**  ",
            f"Source: {source_note}",
            "",
            "### Epic Games",
            render_epic_games(current_games),
            "",
            "### Upcoming on Epic",
            render_upcoming_epic_games(upcoming_games),
            "",
            "### Steam",
            render_steam_games(steam_games),
            END_MARKER,
        ]
    )


def update_readme():
    readme = README_PATH.read_text(encoding="utf-8")
    start_index = readme.find(START_MARKER)
    end_index = readme.find(END_MARKER)

    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise RuntimeError("README auto-update markers were not found.")

    end_index += len(END_MARKER)
    updated = readme[:start_index] + build_auto_section() + readme[end_index:]
    README_PATH.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    update_readme()
