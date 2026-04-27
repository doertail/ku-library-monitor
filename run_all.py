import os
import time
import warnings
from datetime import datetime

import requests
from dotenv import load_dotenv

# urllib3 / LibreSSL 경고 억제
warnings.filterwarnings("ignore")

from monitors.library import main as library_main
from monitors.groupware import main as grw_main
from monitors.everytime import main as et_main

load_dotenv()

MAX_RETRIES = 3
RETRY_DELAY = 30  # 초


def send_error_alert(message: str) -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        requests.post(
            url,
            json={"content": f"⚠️ KU Library Monitor 오류 ({now})\n{message}", "username": "KU Library Monitor"},
            timeout=10,
        )
    except Exception:
        pass


def run_with_retry(name: str, fn) -> bool:
    """fn 실행, 실패 시 MAX_RETRIES회 재시도. 성공 True, 최종 실패 False."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            fn()
            return True
        except Exception as e:
            short_err = str(e).split("\n")[0][:120]
            print(f"  ✗ 실패 ({attempt}/{MAX_RETRIES}): {short_err}")
            if attempt < MAX_RETRIES:
                print(f"  → {RETRY_DELAY}초 후 재시도...")
                time.sleep(RETRY_DELAY)
            else:
                send_error_alert(f"{name} 공지 확인 {MAX_RETRIES}회 모두 실패\n오류: {e}")
    return False


if __name__ == "__main__":
    now = datetime.now()
    print()
    print("=" * 55)
    print(f"  KU Monitor 실행  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    results = {}

    print("\n[1/3] 도서관 공지")
    results["도서관"] = "OK" if run_with_retry("도서관", library_main) else "FAIL"

    print("\n[2/3] 그룹웨어 공지")
    results["그룹웨어"] = "OK" if run_with_retry("그룹웨어", grw_main) else "FAIL"

    print("\n[3/3] 에브리타임 공지")
    results["에브리타임"] = "OK" if run_with_retry("에브리타임", et_main) else "FAIL"

    print()
    print("-" * 55)
    failed = []
    for name, status in results.items():
        mark = "✓" if status == "OK" else "✗"
        print(f"  {mark} {name}: {status}")
        if status == "FAIL":
            failed.append(name)
    print(f"  완료: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 55)
    print()

    # 전체 실패 시 알림
    if failed:
        send_error_alert(f"다음 모니터 실패: {', '.join(failed)}")
