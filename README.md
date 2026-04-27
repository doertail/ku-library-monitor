# KU Library Monitor

고려대학교 도서관 공지 페이지에서 **근로장학생** 모집 공고를 감지하면 Discord로 알림을 보내는 자동화 스크립트.

## 동작 방식

- 하루 4번(9시, 12시, 15시, 18시) cron으로 실행
- `library.korea.ac.kr/about/notice/` 파싱
- 제목에 `근로장학생` 포함 + `마감` 미포함인 새 게시글 발견 시 Discord 웹훅으로 알림
- `seen_ids.json`으로 중복 알림 방지

## 설치

```bash
pip3 install -r requirements.txt
```

## 모듈 구조

`monitors/` 패키지 내 세 개의 모듈이 각각의 공지 소스를 담당합니다:
- `monitors/library.py` — 도서관 공지
- `monitors/groupware.py` — 그룹웨어 공지
- `monitors/everytime.py` — 에브리타임 공지

공유 유틸리티는 `utils/` 패키지에 있습니다:
- `utils/discord.py` — Discord 알림
- `utils/seen_ids.py` — ID 중복 방지

## 설정

`.env` 파일 생성 후 Discord 웹훅 URL 입력:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
KU_PORTAL_ID=<포털 아이디>
KU_PORTAL_PW=<포털 비밀번호>
ET_ID=<에브리타임 아이디>
ET_PW=<에브리타임 비밀번호>
```

## 실행

```bash
python3 run_all.py            # 모든 소스 확인
```

## cron 등록

```bash
crontab -e
```

아래 줄 추가:

```
0 9,12,15,18 * * * cd /path/to/ku-library-monitor && python3 run_all.py >> logs/run_all.log 2>&1
```

## 알림 형식

```
🎓 근로장학생 공지 발견!
제목: [게시글 제목]
링크: https://library.korea.ac.kr/about/notice/...
확인 시각: 2026-03-11 09:00
```
