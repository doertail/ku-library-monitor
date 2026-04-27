import os
import requests
from dotenv import load_dotenv

load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def send_discord(message: str) -> None:
    """Send a message to Discord webhook. Raises ValueError if webhook URL not configured."""
    if not DISCORD_WEBHOOK_URL:
        raise ValueError("DISCORD_WEBHOOK_URL not set in .env")
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=5)
        if not resp.ok:
            print(f"[WARN] Discord webhook failed ({resp.status_code}): {resp.text}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Discord webhook request failed: {e}")


def send_error_alert(module_name: str, error: str) -> None:
    """Send a formatted error alert to Discord."""
    send_discord(f"⚠️ [{module_name}] 오류 발생: {error}")
