# KU Library Monitor

고려대 도서관 공지에서 근로장학생 모집 공고를 감지해 Discord로 알림 보내는 스크립트.

## 한 줄 요약

`monitor.py` 단일 파일. cron으로 하루 2회 실행.

## 기술 스택

- Python 3 + requests + BeautifulSoup4
- Discord Webhook (알림 전송)
- `seen_ids.json` (중복 방지 상태 저장)
- `.env` (DISCORD_WEBHOOK_URL 관리)

## 실행

```bash
python3 monitor.py
```

환경변수 필요: `.env`에 `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`

## 핵심 로직

1. `fetch_notices()` — `library.korea.ac.kr/about/notice/` HTML 파싱
2. 제목에 `근로장학생` 포함 + `마감` 미포함인 게시글만 필터
3. `seen_ids.json`에 없는 새 ID만 Discord 전송 후 저장

## 감지 패턴

```python
KEYWORD = "근로장학생"
# "마감" 포함 게시글은 무시
if KEYWORD in notice["title"] and "마감" not in notice["title"]:
```

## 주요 파일

| 파일 | 역할 |
|------|------|
| `monitor.py` | 메인 스크립트 (전부) |
| `seen_ids.json` | 이미 처리한 공지 ID 목록 |
| `.env` | Discord Webhook URL (git 제외) |
| `requirements.txt` | requests, beautifulsoup4, python-dotenv |

## cron 설정 (하루 2회)

```
0 9,15 * * * cd /path/to/ku-library-monitor && python3 monitor.py >> monitor.log 2>&1
```

## 주의사항

- `seen_ids.json`을 지우면 과거 공지 전체 재알림됨
- 학교 공지 페이지 HTML 구조 변경 시 `table.table` 선택자 깨질 수 있음

## 유용한 Skills

- `/simplify` — 코드 수정 후 품질 리뷰
- `/commit` — 커밋 메시지 자동 작성
