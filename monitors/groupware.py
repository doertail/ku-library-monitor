import os
import re
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from utils.discord import send_discord
from utils.seen_ids import load_seen_ids, save_seen_ids

load_dotenv()

PORTAL_ID = os.getenv("KU_PORTAL_ID", "")
PORTAL_PW = os.getenv("KU_PORTAL_PW", "")
GRW_NOTICE_PATH = "/GroupWare/user/NoticeList.jsp?kind=11"
GRW_NOTICE_URL = "https://grw.korea.ac.kr" + GRW_NOTICE_PATH
KEYWORD = "근로장학생"
SEEN_IDS_PATH = "data/seen_ids_grw.json"

# 본문 후보 CSS 선택자 (우선순위 순)
BODY_SELECTORS = [
    "td.htmlcontent",
    ".board-view-content",
    ".view-content",
    "td.content",
    ".contents",
    "div.content",
    ".bbs-view-content",
]


def fetch_notices(seen_ids: set) -> list[dict]:
    """포털 로그인 후 그룹웨어 공지 목록을 가져오고,
    새 근로장학생 공지는 상세 본문까지 포함해 반환한다."""
    if not PORTAL_ID or not PORTAL_PW:
        print("KU_PORTAL_ID / KU_PORTAL_PW 미설정 — 그룹웨어 모니터 건너뜀")
        return []

    notices = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            # 1. 포털 로그인
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
                return []

            # 2. moveComponent로 그룹웨어 SSO 세션 수립 (grw 쿠키 설정)
            page.evaluate(
                "moveComponent("
                "'https://grw.korea.ac.kr', '3', "
                f"'{GRW_NOTICE_PATH}', '148', '340', 'B'"
                ")"
            )
            page.wait_for_timeout(2000)

            # 3. 같은 context에서 새 탭으로 그룹웨어 직접 접근
            grw_page = context.new_page()
            grw_page.goto(GRW_NOTICE_URL, wait_until="networkidle", timeout=15000)

            # 4. 공지 목록 파싱
            soup = BeautifulSoup(grw_page.content(), "html.parser")
            for a in soup.select("a[href*='view(']"):
                href = a.get("href", "")
                match = re.search(
                    r"view\(\s*'(\d+)'\s*,\s*'(\d+)'\s*,\s*'(\d+)'", href
                )
                if not match:
                    continue
                seq = match.group(3)
                title = a.get_text(strip=True)
                if not title:
                    continue
                notices.append({
                    "id": seq,
                    "title": title,
                    "link": GRW_NOTICE_URL,
                    "href": href,
                    "body": "",
                })

            # 5. 새 근로장학생 공지만 상세 본문 가져오기
            for notice in notices:
                if notice["id"] in seen_ids:
                    continue
                if KEYWORD not in notice["title"] or "마감" in notice["title"]:
                    continue

                try:
                    # view() JS 호출로 상세 페이지 로드
                    m = re.search(
                        r"view\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,"
                        r"\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,"
                        r"\s*'([^']+)'\s*,\s*'([^']+)'",
                        notice["href"],
                    )
                    if m:
                        args = m.groups()
                        grw_page.evaluate(
                            f"view('{args[0]}','{args[1]}','{args[2]}',"
                            f"'{args[3]}','{args[4]}','{args[5]}',"
                            f"'{args[6]}','{args[7]}')"
                        )
                        grw_page.wait_for_timeout(2000)

                    # 본문 추출
                    detail_soup = BeautifulSoup(grw_page.content(), "html.parser")
                    for sel in BODY_SELECTORS:
                        el = detail_soup.select_one(sel)
                        if el and len(el.get_text(strip=True)) > 20:
                            notice["body"] = el.get_text(separator="\n", strip=True)[:800]
                            break

                    # 목록으로 복귀
                    grw_page.goto(GRW_NOTICE_URL, wait_until="networkidle", timeout=15000)

                except Exception as e:
                    print(f"상세 본문 로드 실패: {e}")

        finally:
            context.close()
            browser.close()

    return notices


def main() -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 그룹웨어 공지 확인 시작")

    seen_ids = load_seen_ids(SEEN_IDS_PATH)
    notices = fetch_notices(seen_ids)
    print(f"파싱된 공지 수: {len(notices)}")

    new_count = 0
    for notice in notices:
        if notice["id"] in seen_ids:
            continue
        seen_ids.add(notice["id"])
        if KEYWORD in notice["title"] and "마감" not in notice["title"]:
            print(f"새 근로장학생 공지 발견: {notice['title']}")
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            body_section = f"\n\n{notice['body']}" if notice['body'] else ""
            message = (
                f"🎓 근로장학생 공지 발견! [그룹웨어]\n"
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
