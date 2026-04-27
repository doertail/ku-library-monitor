import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils.discord import send_discord
from utils.seen_ids import load_seen_ids, save_seen_ids

load_dotenv()

ET_ID = os.getenv("ET_ID", "")
ET_PW = os.getenv("ET_PW", "")
BOARD_URL = "https://everytime.kr/496548"
KEYWORD = "모집"
SEEN_IDS_PATH = "data/seen_ids_et.json"
COOKIES_PATH = "data/et_cookies.json"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _save_cookies(context) -> None:
    cookies = context.cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)


def _load_cookies(context) -> bool:
    if not os.path.exists(COOKIES_PATH):
        return False
    with open(COOKIES_PATH, encoding="utf-8") as f:
        cookies = json.load(f)
    if not cookies:
        return False
    context.add_cookies(cookies)
    return True


def _login(page, context, headless: bool) -> bool:
    """로그인 시도. 성공 시 True, 실패 시 False."""
    if not ET_ID or not ET_PW:
        print("ET_ID / ET_PW 미설정 — 에브리타임 모니터 건너뜀")
        return False

    page.goto("https://account.everytime.kr/login", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(3000)  # reCAPTCHA 초기화 대기

    # 사람처럼 한 글자씩 타이핑해야 reCAPTCHA 통과
    page.click("input[name=id]")
    page.wait_for_timeout(500)
    page.type("input[name=id]", ET_ID, delay=80)
    page.wait_for_timeout(600)
    page.click("input[name=password]")
    page.wait_for_timeout(400)
    page.type("input[name=password]", ET_PW, delay=80)
    page.wait_for_timeout(800)

    page.click("input[type=submit]")
    page.wait_for_timeout(7000)

    if "login" in page.url:
        return False

    _save_cookies(context)
    return True


def _is_logged_in(page) -> bool:
    return "login" not in page.url and "account.everytime" not in page.url


def fetch_posts(seen_ids: set) -> list[dict]:
    if not ET_ID or not ET_PW:
        print("ET_ID / ET_PW 미설정 — 에브리타임 모니터 건너뜀")
        return []

    posts = []
    with sync_playwright() as p:
        # 저장된 쿠키로 먼저 시도 (headless)
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(user_agent=UA)
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()

        logged_in = False

        # 저장된 쿠키로 세션 복원 시도
        if _load_cookies(context):
            page.goto(BOARD_URL, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(1000)
            if _is_logged_in(page):
                logged_in = True
                print("저장된 쿠키로 세션 복원 성공")

        if not logged_in:
            context.close()
            browser.close()

            # 쿠키 없거나 만료 → headless=False로 재로그인
            print("세션 만료 또는 쿠키 없음 — 브라우저 로그인 시도")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(user_agent=UA)
            page = context.new_page()

            if not _login(page, context, headless=False):
                print("에브리타임 로그인 실패 — ET_ID/ET_PW를 확인하세요")
                context.close()
                browser.close()
                return []

            page.goto(BOARD_URL, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(1500)
            print("로그인 성공, 쿠키 저장됨")

        try:
            # 게시글 목록 파싱
            soup = BeautifulSoup(page.content(), "html.parser")
            for article in soup.select("article"):
                a_tag = article.select_one("a.article")
                if not a_tag:
                    continue
                href = a_tag.get("href", "")
                match = re.search(r"/(\d+)$", href)
                if not match:
                    continue
                post_id = match.group(1)
                title_el = a_tag.select_one("h2.medium")
                title = title_el.get_text(strip=True) if title_el else a_tag.get_text(strip=True)
                if not title:
                    continue
                link = "https://everytime.kr" + href if href.startswith("/") else href
                posts.append({"id": post_id, "title": title, "link": link, "body": ""})

            # 새 모집 게시글만 본문 가져오기
            for post in posts:
                if post["id"] in seen_ids:
                    continue
                if KEYWORD not in post["title"]:
                    continue
                try:
                    page.goto(post["link"], wait_until="networkidle", timeout=15000)
                    page.wait_for_timeout(1000)
                    detail_soup = BeautifulSoup(page.content(), "html.parser")
                    for sel in ["p.large", ".text", "p"]:
                        el = detail_soup.select_one(sel)
                        if el and len(el.get_text(strip=True)) > 10:
                            post["body"] = el.get_text(separator="\n", strip=True)[:800]
                            break
                except Exception as e:
                    print(f"본문 로드 실패 ({post['link']}): {e}")

        finally:
            context.close()
            browser.close()

    return posts


def main() -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 에브리타임 공지 확인 시작")

    seen_ids = load_seen_ids(SEEN_IDS_PATH)
    posts = fetch_posts(seen_ids)
    print(f"파싱된 게시글 수: {len(posts)}")

    new_count = 0
    for post in posts:
        if post["id"] in seen_ids:
            continue
        seen_ids.add(post["id"])
        if KEYWORD in post["title"]:
            print(f"새 모집 공지 발견: {post['title']}")
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            body_section = f"\n\n{post['body']}" if post["body"] else ""
            message = (
                f"📢 근장 모집 공지 발견! [에브리타임]\n"
                f"제목: {post['title']}\n"
                f"링크: {post['link']}\n"
                f"확인 시각: {now}"
                f"{body_section}"
            )
            send_discord(message)
            new_count += 1

    save_seen_ids(SEEN_IDS_PATH, seen_ids)
    print(f"완료 — 새 모집 공지: {new_count}건")


if __name__ == "__main__":
    main()
