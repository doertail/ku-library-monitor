# KU Library Monitor

고려대학교 도서관 공지 페이지에서 **근로장학생** 모집 공고를 감지하면 Discord로 알림을 보내는 자동화 스크립트.

## 동작 방식

- 하루 2번(오전 9시, 오후 3시) cron으로 실행
- `library.korea.ac.kr/about/notice/` 파싱
- 제목에 `근로장학생` 포함 + `마감` 미포함인 새 게시글 발견 시 Discord 웹훅으로 알림
- `seen_ids.json`으로 중복 알림 방지

## 설치

```bash
pip3 install -r requirements.txt
```

## 설정

`.env` 파일 생성 후 Discord 웹훅 URL 입력:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## 실행

```bash
python3 monitor.py
```

## cron 등록

```bash
crontab -e
```

아래 줄 추가:

```
0 9,15 * * * cd /path/to/ku-library-monitor && python3 monitor.py >> monitor.log 2>&1
```

## 알림 형식

```
🎓 근로장학생 공지 발견!
제목: [게시글 제목]
링크: https://library.korea.ac.kr/about/notice/...
확인 시각: 2026-03-11 09:00
```
