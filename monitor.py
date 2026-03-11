import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://library.korea.ac.kr"
NOTICE_URL = f"{BASE_URL}/about/notice/"
SEEN_IDS_FILE = Path(__file__).parent / "seen_ids.json"
KEYWORD = "근로장학생"


def fetch_notices() -> list[dict]:
    resp = requests.get(NOTICE_URL, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    notices = []
    table = soup.select_one("table.kboard-list-table")
    if not table:
        print("공지 테이블을 찾을 수 없습니다.")
        return notices

    for tr in table.select("tr"):
        a_tag = tr.select_one("td a")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        # Extract numeric post ID from URL
        match = re.search(r"/(\d+)/?$", href) or re.search(r"[?&](?:no|id|idx)=(\d+)", href)
        if not match:
            continue
        post_id = match.group(1)
        link = href if href.startswith("http") else BASE_URL + href
        notices.append({"id": post_id, "title": title, "link": link})

    return notices


def load_seen_ids() -> set:
    if SEEN_IDS_FILE.exists():
        with open(SEEN_IDS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen_ids: set) -> None:
    with open(SEEN_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_ids), f, ensure_ascii=False, indent=2)


def send_discord(title: str, link: str) -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        print("DISCORD_WEBHOOK_URL 미설정 — 알림 건너뜀")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = (
        f"🎓 근로장학생 공지 발견!\n"
        f"제목: {title}\n"
        f"링크: {link}\n"
        f"확인 시각: {now}"
    )
    try:
        resp = requests.post(
            url,
            json={"content": message, "username": "KU Library Monitor"},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"Discord 알림 전송 완료: {title}")
    except Exception as e:
        print(f"Discord 전송 실패: {e}")


def main() -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 공지 확인 시작")

    notices = fetch_notices()
    print(f"파싱된 공지 수: {len(notices)}")

    seen_ids = load_seen_ids()
    new_count = 0

    for notice in notices:
        if notice["id"] in seen_ids:
            continue
        seen_ids.add(notice["id"])
        if KEYWORD in notice["title"] and "마감" not in notice["title"]:
            print(f"새 근로장학생 공지 발견: {notice['title']}")
            send_discord(notice["title"], notice["link"])
            new_count += 1

    save_seen_ids(seen_ids)
    print(f"완료 — 새 근로장학생 공지: {new_count}건")


if __name__ == "__main__":
    main()
