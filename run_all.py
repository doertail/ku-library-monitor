import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

from monitor import main as library_main
from monitor_grw import main as grw_main

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


if __name__ == "__main__":
    library_main()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            grw_main()
            break
        except Exception as e:
            print(f"그룹웨어 실패 ({attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                print(f"{RETRY_DELAY}초 후 재시도...")
                time.sleep(RETRY_DELAY)
            else:
                print("최대 재시도 횟수 초과 — 다음 cron 실행 시 재시도됩니다.")
                send_error_alert(f"그룹웨어 공지 확인 {MAX_RETRIES}회 모두 실패\n오류: {e}")
