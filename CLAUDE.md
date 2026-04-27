# KU Library Monitor

고려대 도서관 공지 + 그룹웨어 공지에서 근로장학생 모집 공고를 감지해 Discord로 알림 보내는 스크립트.

## 한 줄 요약

`run_all.py` 실행 시 `monitor.py`(도서관)와 `monitor_grw.py`(그룹웨어) 순차 실행. cron 하루 2회.

## 기술 스택

- Python 3 + requests + BeautifulSoup4
- Playwright (그룹웨어 SSO 로그인, 에브리타임 로그인용)
- Discord Webhook (알림 전송)
- `seen_ids.json` / `seen_ids_grw.json` / `seen_ids_et.json` (중복 방지 상태 저장)
- `.env` (환경변수 관리)

## 실행

```bash
python3 run_all.py            # 전체 실행 (도서관 + 그룹웨어 + 에브리타임)
python3 monitor.py            # 도서관 공지만
python3 monitor_grw.py        # 그룹웨어 공지만
python3 monitor_everytime.py  # 에브리타임 근장게시판만
```

환경변수 필요 (`.env`):
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
KU_PORTAL_ID=<포털 아이디>
KU_PORTAL_PW=<포털 비밀번호>
ET_ID=<에브리타임 아이디>
ET_PW=<에브리타임 비밀번호>
```

## 핵심 로직

### monitor.py (도서관 공지)
1. `fetch_notices()` — `library.korea.ac.kr/about/notice/` HTML 파싱
2. 제목에 `근로장학생` 포함 + `마감` 미포함인 게시글만 필터
3. `seen_ids.json`에 없는 새 ID만 Discord 전송 후 저장

### monitor_grw.py (그룹웨어 공지)
1. Playwright로 `portal.korea.ac.kr` 로그인
2. `moveComponent()`로 그룹웨어 SSO 세션 수립 (grw 쿠키 설정)
3. 같은 browser context의 새 탭으로 `grw.korea.ac.kr` 직접 접근
4. 공지 목록 파싱 → 새 근로장학생 공지는 `view()` JS 호출로 상세 진입
5. 본문 (`td.htmlcontent`) 추출 후 Discord 전송
6. `seen_ids_grw.json`으로 중복 방지

## 감지 패턴

```python
KEYWORD = "근로장학생"
# "마감" 포함 게시글은 무시
if KEYWORD in notice["title"] and "마감" not in notice["title"]:
```

## 주요 파일

| 파일 | 역할 |
|------|------|
| `run_all.py` | 전체 실행 진입점 |
| `monitor.py` | 도서관 공지 스크립트 |
| `monitor_grw.py` | 그룹웨어 공지 스크립트 (Playwright) |
| `monitor_everytime.py` | 에브리타임 근장게시판 스크립트 (Playwright) |
| `seen_ids.json` | 도서관 처리 공지 ID 목록 |
| `seen_ids_grw.json` | 그룹웨어 처리 공지 ID 목록 |
| `seen_ids_et.json` | 에브리타임 처리 게시글 ID 목록 |
| `.env` | 환경변수 (git 제외) |
| `requirements.txt` | 의존성 목록 |

## cron 설정 (하루 2회: 9시, 15시)

```
0 9,15 * * * cd /Users/jihun/workspace/ku-library-monitor && /usr/bin/python3 run_all.py >> run_all.log 2>&1
```

## 주의사항

- `seen_ids.json` / `seen_ids_grw.json` 을 지우면 과거 공지 전체 재알림됨
- 도서관 공지 HTML 구조 변경 시 `table.table` 선택자 깨질 수 있음
- 그룹웨어 본문 선택자: `td.htmlcontent` (변경 시 `BODY_SELECTORS` 수정)
- 그룹웨어는 Playwright + Chromium 필요 (`playwright install chromium`)

## 유용한 Skills

- `/simplify` — 코드 수정 후 품질 리뷰
- `/commit` — 커밋 메시지 자동 작성
