import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from utils.discord import send_discord
from utils.seen_ids import load_seen_ids, save_seen_ids

load_dotenv()

BASE_URL = "https://library.korea.ac.kr"
NOTICE_URL = f"{BASE_URL}/about/notice/"
SEEN_IDS_PATH = "data/seen_ids.json"
KEYWORD = "근로장학생"


def fetch_notices() -> list[dict]:
    resp = requests.get(NOTICE_URL, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    notices = []
    table = soup.select_one("table.table")
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
        match = re.search(r"/(\d+)/?$", href) or re.search(r"[?&](?:no|uid|id|idx)=(\d+)", href)
        if not match:
            continue
        post_id = match.group(1)
        link = href if href.startswith("http") else BASE_URL + href
        notices.append({"id": post_id, "title": title, "link": link, "body": ""})

    return notices


def fetch_body(link: str) -> str:
    try:
        resp = requests.get(link, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        el = soup.select_one(".kboard-content")
        if el:
            return el.get_text(separator="\n", strip=True)[:800]
    except Exception as e:
        print(f"본문 가져오기 실패: {e}")
    return ""


def main() -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 공지 확인 시작")

    notices = fetch_notices()
    print(f"파싱된 공지 수: {len(notices)}")

    seen_ids = load_seen_ids(SEEN_IDS_PATH)
    new_count = 0

    for notice in notices:
        if notice["id"] in seen_ids:
            continue
        seen_ids.add(notice["id"])
        if KEYWORD in notice["title"] and "마감" not in notice["title"]:
            print(f"새 근로장학생 공지 발견: {notice['title']}")
            body = fetch_body(notice["link"])
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            body_section = f"\n\n{body}" if body else ""
            message = (
                f"🎓 근로장학생 공지 발견!\n"
                f"제목: {notice['title']}\n"
                f"링크: {notice['link']}\n"
                f"확인 시각: {now}"
                f"{body_section}"
            )
            send_discord(message)
            new_count += 1

    save_seen_ids(SEEN_IDS_PATH, seen_ids)
    print(f"완료 — 새 근로장학생 공지: {new_count}건")


if __name__ == "__main__":
    main()
