# 발송 채널 설정 가이드

`scripts/deliver.py`는 4개 채널로 리포트를 보낸다: **파일(항상) / macOS 알림 / 이메일 / 텔레그램**.
설정은 `delivery-config.example.json`을 `delivery-config.json`으로 복사한 뒤 채운다. 비밀값은 config에 직접 넣거나 환경변수로 주입한다.

## 1. 파일 저장 (기본, 설정 불필요)
리포트는 항상 `reports/YYYY-MM-DD-realestate-daily.md`에 저장된다.

## 2. macOS 데스크톱 알림 (기본 켜짐, 설정 불필요)
`channels.notification.enabled: true`면 실행 완료 시 핵심 요약이 알림으로 뜬다. osascript 사용.

## 3. 이메일 (선택)
1. `channels.email.enabled: true`로 변경.
2. Gmail 사용 시: 계정 2단계 인증 활성화 → **앱 비밀번호** 발급(https://myaccount.google.com/apppasswords) → `smtp_password`에 입력. **일반 로그인 비번은 작동하지 않는다.**
3. 또는 환경변수로: `export RE_NEWS_SMTP_USER=... RE_NEWS_SMTP_PASSWORD=...`
4. `to`에 받을 주소(기본 algo1744@gmail.com).

## 4. 텔레그램 (선택)
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` → 봇 이름 지정 → **bot_token** 받기.
2. 만든 봇과 대화 시작(아무 메시지나 전송).
3. 브라우저에서 `https://api.telegram.org/bot<TOKEN>/getUpdates` 열기 → 응답 JSON의 `result[].message.chat.id`가 **chat_id**.
4. `channels.telegram.enabled: true`, `bot_token`, `chat_id` 입력. 또는 환경변수 `RE_NEWS_TG_TOKEN` / `RE_NEWS_TG_CHATID`.

## 테스트
```bash
python3 .claude/skills/realestate-news-daily/scripts/deliver.py \
  --report reports/테스트.md --summary _workspace/테스트/summary.txt
```
각 채널 결과가 ✅/❌로 출력된다. 활성화 안 된 채널은 "disabled (skip)".

## 보안
`delivery-config.json`은 비밀값을 담는다. git 사용 시 `.gitignore`에 추가하라(이미 추가됨).
