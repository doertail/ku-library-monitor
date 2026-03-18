import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

PORTAL_ID = os.getenv("KU_PORTAL_ID", "")
PORTAL_PW = os.getenv("KU_PORTAL_PW", "")
GRW_NOTICE_PATH = "/GroupWare/user/NoticeList.jsp?kind=11"
GRW_NOTICE_URL = "https://grw.korea.ac.kr" + GRW_NOTICE_PATH
KEYWORD = "근로장학생"
SEEN_IDS_FILE = Path(__file__).parent / "seen_ids_grw.json"


def _get_sso_token() -> dict | None:
    """포털 로그인 후 그룹웨어 SSO 토큰을 추출한다."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(
                "https://portal.korea.ac.kr",
                wait_until="networkidle",
                timeout=20000,
            )
            page.fill("#oneid", PORTAL_ID)
            page.fill("#_pw", PORTAL_PW)
            with page.expect_navigation(wait_until="networkidle", timeout=20000):
                page.click("#loginsubmit")

            if "Intro.kpd" in page.url or "LoginDeny" in page.url:
                print("포털 로그인 실패 — ID/PW를 확인하세요")
                return None

            # moveComponent로 SSO 토큰이 담긴 _compForm 로드
            page.evaluate(
                "moveComponent("
                "'https://grw.korea.ac.kr', '3', "
                f"'{GRW_NOTICE_PATH}', '148', '340', 'B'"
                ")"
            )
            page.wait_for_timeout(2000)

            lock_frame = page.frame(name="lockMenuCheck")
            if not lock_frame:
                print("lockMenuCheck 프레임을 찾을 수 없습니다")
                return None

            form_data = lock_frame.evaluate(
                """() => {
                const form = document.getElementById('_compForm');
                if (!form) return null;
                const data = {};
                for (const el of form.elements) {
                    if (el.name) data[el.name] = el.value;
                }
                return data;
            }"""
            )
            return form_data
        finally:
            browser.close()


def fetch_notices() -> list[dict]:
    if not PORTAL_ID or not PORTAL_PW:
        print("KU_PORTAL_ID / KU_PORTAL_PW 미설정 — 그룹웨어 모니터 건너뜀")
        return []

    form_data = _get_sso_token()
    if not form_data:
        return []

    # SSO 토큰으로 그룹웨어 공지 페이지 요청
    resp = requests.post(GRW_NOTICE_URL, data=form_data, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    notices = []
    for a in soup.select("a[href*='view(']"):
        href = a.get("href", "")
        match = re.search(r"view\(\s*'\d+'\s*,\s*'(\d+)'\s*,\s*'(\d+)'", href)
        if not match:
            continue
        post_id = match.group(2)
        title = a.get_text(strip=True)
        if not title:
            continue
        notices.append({"id": post_id, "title": title, "link": GRW_NOTICE_URL})

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
        f"🎓 근로장학생 공지 발견! [그룹웨어]\n"
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 그룹웨어 공지 확인 시작")

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
